"""Signal Contract repository."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from backend.models.signal_contract import SignalContract
from backend.repositories.base import BaseRepository


class SignalContractRepository(BaseRepository[SignalContract]):
    """Repository for signal contract operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(SignalContract, db)

    @staticmethod
    def _apply_org_scope(
        query: Select,
        *,
        org_id: UUID | None = None,
        include_global: bool = False,
    ) -> Select:
        """Scope contract queries to an org, optionally including global contracts."""
        if org_id is None:
            return query
        if include_global:
            return query.where(
                or_(SignalContract.org_id == org_id, SignalContract.org_id.is_(None))
            )
        return query.where(SignalContract.org_id == org_id)

    async def get_scoped(
        self,
        contract_id: UUID,
        *,
        org_id: UUID | None = None,
        include_global: bool = False,
    ) -> SignalContract | None:
        """Get a contract by ID with tenant scoping."""
        query = select(SignalContract).where(SignalContract.id == contract_id)
        query = self._apply_org_scope(
            query,
            org_id=org_id,
            include_global=include_global,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_contracts(
        self,
        *,
        org_id: UUID | None = None,
        include_global: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SignalContract]:
        """Get active contracts, optionally scoped to an org."""
        query = select(SignalContract).where(
            SignalContract.is_active.is_(True),
            SignalContract.status == "active",
        )
        query = self._apply_org_scope(
            query,
            org_id=org_id,
            include_global=include_global,
        )
        result = await self.db.execute(
            query.order_by(SignalContract.name).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_industry(
        self,
        industry_id: UUID,
        *,
        org_id: UUID | None = None,
        include_global: bool = False,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SignalContract]:
        """Get signal contracts for a given industry."""
        query = select(SignalContract).where(SignalContract.industry_id == industry_id)
        if active_only:
            query = query.where(
                SignalContract.is_active.is_(True),
                SignalContract.status == "active",
            )
        query = self._apply_org_scope(
            query,
            org_id=org_id,
            include_global=include_global,
        )
        result = await self.db.execute(
            query.order_by(SignalContract.name).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_source_type(
        self,
        source_type: str,
        *,
        org_id: UUID | None = None,
        include_global: bool = False,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SignalContract]:
        """Get contracts by source type."""
        query = select(SignalContract).where(SignalContract.source_type == source_type)
        if active_only:
            query = query.where(
                SignalContract.is_active.is_(True),
                SignalContract.status == "active",
            )
        query = self._apply_org_scope(
            query,
            org_id=org_id,
            include_global=include_global,
        )
        result = await self.db.execute(
            query.order_by(SignalContract.name).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_schedule_tier(
        self,
        tier: str,
        *,
        org_id: UUID | None = None,
        include_global: bool = True,
    ) -> list[SignalContract]:
        """Get active contracts by schedule tier."""
        query = select(SignalContract).where(
            SignalContract.schedule_tier == tier,
            SignalContract.is_active.is_(True),
            SignalContract.status == "active",
        )
        query = self._apply_org_scope(
            query,
            org_id=org_id,
            include_global=include_global,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_due_for_fetch(
        self,
        before: datetime,
        *,
        org_id: UUID | None = None,
        include_global: bool = True,
    ) -> list[SignalContract]:
        """Get active contracts that haven't been fetched since `before` timestamp."""
        query = select(SignalContract).where(
            SignalContract.is_active.is_(True),
            SignalContract.status.in_(["active", "degraded"]),
            (
                SignalContract.last_fetched_at.is_(None)
                | (SignalContract.last_fetched_at < before)
            ),
        )
        query = self._apply_org_scope(
            query,
            org_id=org_id,
            include_global=include_global,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_scoped(
        self,
        *,
        org_id: UUID | None = None,
        include_global: bool = False,
        industry_id: UUID | None = None,
        source_type: str | None = None,
        active_only: bool | None = None,
        degraded_only: bool = False,
    ) -> int:
        """Count contracts with optional org scoping and filters."""
        query = select(func.count(SignalContract.id))

        if industry_id is not None:
            query = query.where(SignalContract.industry_id == industry_id)
        if source_type is not None:
            query = query.where(SignalContract.source_type == source_type)
        if active_only is True:
            query = query.where(
                SignalContract.is_active.is_(True),
                SignalContract.status == "active",
            )
        elif active_only is False:
            query = query.where(SignalContract.is_active.is_(False))
        if degraded_only:
            query = query.where(SignalContract.status == "degraded")

        query = self._apply_org_scope(
            query,
            org_id=org_id,
            include_global=include_global,
        )
        result = await self.db.execute(query)
        return result.scalar_one()

    async def mark_fetched(
        self,
        contract_id: UUID,
        *,
        reset_failures: bool = True,
    ) -> SignalContract | None:
        """Mark a contract as successfully fetched."""
        update_data = {
            "last_fetched_at": datetime.now(timezone.utc),
            "last_error": None,
        }
        if reset_failures:
            update_data["failure_count"] = 0
            update_data["status"] = "active"
        return await self.update(contract_id, **update_data)

    async def mark_failed(
        self,
        contract_id: UUID,
        error_message: str,
    ) -> SignalContract | None:
        """Record a fetch failure and degrade after max failures."""
        contract = await self.get(contract_id)
        if not contract:
            return None

        new_failure_count = contract.failure_count + 1
        new_status = (
            "degraded"
            if new_failure_count >= contract.max_failures
            else contract.status
        )
        return await self.update(
            contract_id,
            failure_count=new_failure_count,
            status=new_status,
            last_error=error_message,
        )

    async def get_degraded_contracts(
        self,
        *,
        org_id: UUID | None = None,
        include_global: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SignalContract]:
        """Get degraded contracts with optional org scoping."""
        query = select(SignalContract).where(SignalContract.status == "degraded")
        query = self._apply_org_scope(
            query,
            org_id=org_id,
            include_global=include_global,
        )
        result = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())
