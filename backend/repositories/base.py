"""Base repository with CRUD operations and tenant isolation"""

import time
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import Select, and_, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.base import Base
from backend.repositories.audit import audit_logger

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository with common CRUD operations"""

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: UUID) -> ModelType | None:
        """Get a single record by ID"""
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: List[UUID]) -> List[ModelType]:
        """Get multiple records by their IDs (bulk fetch)"""
        if not ids:
            return []

        result = await self.db.execute(select(self.model).where(self.model.id.in_(ids)))
        return list(result.scalars().all())

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> List[ModelType]:
        """
        Get multiple records with pagination, filtering, and sorting.

        Args:
            skip: Number of records to skip (pagination offset)
            limit: Maximum number of records to return
            filters: Dictionary of field:value pairs to filter by
            sort_by: Field name to sort by (default: created_at)
            sort_desc: Sort descending if True, ascending if False

        Returns:
            List of model instances
        """
        query = select(self.model)

        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

        # Apply sorting
        if hasattr(self.model, sort_by):
            sort_column = getattr(self.model, sort_by)
            query = query.order_by(desc(sort_column) if sort_desc else sort_column)

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records matching filters.

        Args:
            filters: Dictionary of field:value pairs to filter by

        Returns:
            Total count of matching records
        """
        query = select(func.count(self.model.id))

        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new record"""
        db_obj = self.model(**kwargs)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def create_many(self, items: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in a single transaction (bulk insert).

        Args:
            items: List of dictionaries with field:value pairs

        Returns:
            List of created model instances
        """
        if not items:
            return []

        db_objects = [self.model(**item) for item in items]
        self.db.add_all(db_objects)
        await self.db.flush()

        # For async operations, just return the objects without refresh
        # They will have their IDs from the flush operation
        return db_objects

    async def update(self, id: UUID, **kwargs: Any) -> ModelType | None:
        """Update an existing record"""
        db_obj = await self.get(id)
        if not db_obj:
            return None

        for field, value in kwargs.items():
            setattr(db_obj, field, value)

        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update_many(self, updates: List[Dict[str, Any]]) -> int:
        """
        Update multiple records in a single transaction (bulk update).
        Each dict must include 'id' field.

        Args:
            updates: List of dicts with 'id' and fields to update

        Returns:
            Number of records updated
        """
        if not updates:
            return 0

        updated_count = 0
        for update_data in updates:
            if "id" not in update_data:
                continue

            record_id = update_data.pop("id")
            db_obj = await self.get(record_id)

            if db_obj:
                for field, value in update_data.items():
                    setattr(db_obj, field, value)
                updated_count += 1

        await self.db.flush()
        return updated_count

    async def delete(self, id: UUID) -> bool:
        """Hard delete a record"""
        db_obj = await self.get(id)
        if not db_obj:
            return False

        await self.db.delete(db_obj)
        await self.db.flush()
        return True

    async def delete_many(self, ids: List[UUID]) -> int:
        """
        Delete multiple records in a single transaction (bulk delete).

        Args:
            ids: List of record IDs to delete

        Returns:
            Number of records deleted
        """
        if not ids:
            return 0

        result = await self.db.execute(delete(self.model).where(self.model.id.in_(ids)))
        await self.db.flush()
        return result.rowcount

    async def soft_delete(self, id: UUID) -> ModelType | None:
        """Soft delete a record (if model has deleted_at)"""
        db_obj = await self.get(id)
        if not db_obj:
            return None

        if hasattr(db_obj, "deleted_at"):
            db_obj.deleted_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(db_obj)

        return db_obj

    async def exists(self, id: UUID) -> bool:
        """Check if a record exists by ID"""
        result = await self.db.execute(
            select(func.count(self.model.id)).where(self.model.id == id)
        )
        return result.scalar_one() > 0


class TenantRepository(BaseRepository[ModelType]):
    """Repository with multi-tenant isolation and audit logging"""

    def __init__(
        self,
        model: Type[ModelType],
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID | None = None,
        request_id: str | None = None,
    ):
        super().__init__(model, db)
        self.org_id = org_id
        self.user_id = user_id
        self.request_id = request_id
        self.table_name = (
            model.__tablename__
            if hasattr(model, "__tablename__")
            else model.__name__.lower()
        )

    async def get(self, id: UUID) -> ModelType | None:
        """Get record by ID (tenant-scoped)"""
        start_time = time.time()

        result = await self.db.execute(
            select(self.model).where(
                and_(self.model.id == id, self.model.org_id == self.org_id)
            )
        )
        record = result.scalar_one_or_none()

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=self.org_id,
            table=self.table_name,
            action="get",
            filters={"id": id},
            result_count=1 if record else 0,
            duration_ms=duration_ms,
            request_id=self.request_id,
            resource_ids=[id] if record else None,
        )

        return record

    async def get_by_ids(self, ids: List[UUID]) -> List[ModelType]:
        """Get multiple records by IDs (tenant-scoped)"""
        if not ids:
            return []

        result = await self.db.execute(
            select(self.model).where(
                and_(self.model.id.in_(ids), self.model.org_id == self.org_id)
            )
        )
        return list(result.scalars().all())

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> List[ModelType]:
        """Get multiple records (tenant-scoped with filtering)"""
        start_time = time.time()

        query = select(self.model).where(self.model.org_id == self.org_id)

        # Apply additional filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

        # Apply sorting
        if hasattr(self.model, sort_by):
            sort_column = getattr(self.model, sort_by)
            query = query.order_by(desc(sort_column) if sort_desc else sort_column)

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        records = list(result.scalars().all())

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=self.org_id,
            table=self.table_name,
            action="list",
            filters=filters or {},
            result_count=len(records),
            duration_ms=duration_ms,
            request_id=self.request_id,
        )

        return records

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records in tenant (with optional filters)"""
        query = select(func.count(self.model.id)).where(
            self.model.org_id == self.org_id
        )

        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelType:
        """Create record with automatic org_id injection"""
        start_time = time.time()

        kwargs["org_id"] = self.org_id
        record = await super().create(**kwargs)

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=self.org_id,
            table=self.table_name,
            action="create",
            result_count=1,
            duration_ms=duration_ms,
            request_id=self.request_id,
            resource_ids=[record.id],
        )

        return record

    async def create_many(self, items: List[Dict[str, Any]]) -> List[ModelType]:
        """Create multiple records with automatic org_id injection"""
        # Inject org_id into all items
        for item in items:
            item["org_id"] = self.org_id

        return await super().create_many(items)

    async def update(self, id: UUID, **kwargs: Any) -> ModelType | None:
        """Update record (tenant-scoped)"""
        start_time = time.time()

        # First verify record exists in this org
        db_obj = await self.get(id)
        if not db_obj:
            audit_logger.log_cross_org_attempt(
                user_id=self.user_id,
                user_org_id=self.org_id,
                attempted_org_id=self.org_id,  # Unknown actual org
                table=self.table_name,
                action="update",
                resource_id=id,
                request_id=self.request_id,
            )
            return None

        for field, value in kwargs.items():
            if field != "org_id":  # Prevent org_id hijacking
                setattr(db_obj, field, value)

        await self.db.flush()
        await self.db.refresh(db_obj)

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=self.org_id,
            table=self.table_name,
            action="update",
            filters={"id": id},
            result_count=1,
            duration_ms=duration_ms,
            request_id=self.request_id,
            resource_ids=[id],
        )

        return db_obj

    async def delete(self, id: UUID) -> bool:
        """Hard delete record (tenant-scoped)"""
        start_time = time.time()

        # Verify record exists in this org before deleting
        db_obj = await self.get(id)
        if not db_obj:
            return False

        await self.db.delete(db_obj)
        await self.db.flush()

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=self.org_id,
            table=self.table_name,
            action="delete",
            filters={"id": id},
            result_count=1,
            duration_ms=duration_ms,
            request_id=self.request_id,
            resource_ids=[id],
        )

        return True

    async def delete_many(self, ids: List[UUID]) -> int:
        """Delete multiple records (tenant-scoped)"""
        if not ids:
            return 0

        start_time = time.time()

        result = await self.db.execute(
            delete(self.model).where(
                and_(self.model.id.in_(ids), self.model.org_id == self.org_id)
            )
        )
        await self.db.flush()
        deleted_count = result.rowcount

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=self.org_id,
            table=self.table_name,
            action="delete_many",
            filters={"ids": ids},
            result_count=deleted_count,
            duration_ms=duration_ms,
            request_id=self.request_id,
            resource_ids=ids,
        )

        return deleted_count

    async def exists(self, id: UUID) -> bool:
        """Check if a record exists in tenant"""
        result = await self.db.execute(
            select(func.count(self.model.id)).where(
                and_(self.model.id == id, self.model.org_id == self.org_id)
            )
        )
        return result.scalar_one() > 0

    async def verify_org_access(self, resource_id: UUID) -> bool:
        """
        Verify a resource belongs to the current org.
        Logs cross-org access attempts.

        Args:
            resource_id: Resource ID to check

        Returns:
            True if resource belongs to org, False otherwise
        """
        result = await self.db.execute(
            select(self.model.org_id).where(self.model.id == resource_id)
        )
        actual_org_id = result.scalar_one_or_none()

        if actual_org_id is None:
            return False  # Resource doesn't exist

        if actual_org_id != self.org_id:
            # Log security violation
            audit_logger.log_cross_org_attempt(
                user_id=self.user_id,
                user_org_id=self.org_id,
                attempted_org_id=actual_org_id,
                table=self.table_name,
                action="verify_access",
                resource_id=resource_id,
                request_id=self.request_id,
            )
            return False

        return True

    async def list_by_owner(self, owner_id: UUID, limit: int = 100) -> List[ModelType]:
        """
        List resources owned by a specific user (within current org).
        Useful for 'My Documents', 'My Tasks', etc.
        """
        start_time = time.time()

        # Ensure model has owner_id or created_by field
        owner_field = None
        if hasattr(self.model, "owner_id"):
            owner_field = self.model.owner_id
        elif hasattr(self.model, "created_by"):
            owner_field = self.model.created_by
        else:
            return []

        result = await self.db.execute(
            select(self.model)
            .where(and_(self.model.org_id == self.org_id, owner_field == owner_id))
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        records = list(result.scalars().all())

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=self.org_id,
            table=self.table_name,
            action="list_by_owner",
            filters={"owner_id": owner_id},
            result_count=len(records),
            duration_ms=duration_ms,
            request_id=self.request_id,
        )

        return records
