"""Document repository"""

import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.document import Document
from backend.repositories.base import TenantRepository
from backend.repositories.audit import audit_logger


class DocumentRepository(TenantRepository[Document]):
    """Repository for document operations with audit logging"""
    
    def __init__(self, db: AsyncSession, org_id: UUID, user_id: UUID | None = None, request_id: str | None = None):
        super().__init__(Document, db, org_id, user_id, request_id)
    
    async def get_by_owner(
        self,
        owner_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        """Get documents by owner with audit logging"""
        start_time = time.time()
        
        result = await self.db.execute(
            select(Document)
            .where(
                Document.org_id == self.org_id,
                Document.owner_id == owner_id,
                Document.deleted_at.is_(None)
            )
            .offset(skip)
            .limit(limit)
        )
        records = list(result.scalars().all())
        
        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=self.org_id,
            table="documents",
            action="list_by_owner",
            filters={"owner_id": owner_id},
            result_count=len(records),
            duration_ms=duration_ms,
            request_id=self.request_id,
        )
        
        return records
    
    async def get_by_status(
        self,
        status: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        """Get documents by processing status with audit logging"""
        start_time = time.time()
        
        result = await self.db.execute(
            select(Document)
            .where(
                Document.org_id == self.org_id,
                Document.processing_status == status,
                Document.deleted_at.is_(None)
            )
            .offset(skip)
            .limit(limit)
        )
        records = list(result.scalars().all())
        
        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=self.org_id,
            table="documents",
            action="list_by_status",
            filters={"status": status},
            result_count=len(records),
            duration_ms=duration_ms,
            request_id=self.request_id,
        )
        
        return records
    
    async def get_total_storage_bytes(self) -> int:
        """Get total storage used by organization (in bytes) with audit logging"""
        from sqlalchemy import func
        
        start_time = time.time()
        
        result = await self.db.execute(
            select(func.sum(Document.size_bytes))
            .where(
                Document.org_id == self.org_id,
                Document.deleted_at.is_(None)
            )
        )
        total = result.scalar_one()
        
        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=self.org_id,
            table="documents",
            action="get_storage_total",
            filters={},
            result_count=1,
            duration_ms=duration_ms,
            request_id=self.request_id,
        )
        
        return total or 0
