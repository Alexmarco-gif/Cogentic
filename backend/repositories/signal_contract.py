"""Signal Contract repository"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.signal_contract import SignalContract
from backend.repositories.base import BaseRepository


class SignalContractRepository(BaseRepository[SignalContract]):
    """Repository for signal contract operations.

    Signal contracts are global (not tenant-scoped). 280 seeded across
    4 industries (70 per industry).
    """

    def __init__(self, db: AsyncSession):
        super().__init__(SignalContract, db)

    async def get_active_contracts(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SignalContract]:
        """Get all active signal contracts"""
        result = await self.db.execute(
            select(SignalContract)
            .where(
                SignalContract.is_active.is_(True),
                SignalContract.status == "active",
            )
            .order_by(SignalContract.name)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_industry(
        self,
        industry_id: UUID,
        *,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SignalContract]:
        """Get signal contracts for a given industry"""
        query = select(SignalContract).where(SignalContract.industry_id == industry_id)
        if active_only:
            query = query.where(
                SignalContract.is_active.is_(True),
                SignalContract.status == "active",
            )
        result = await self.db.execute(
            query.order_by(SignalContract.name).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_source_type(
        self,
        source_type: str,
        *,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SignalContract]:
        """Get contracts by source type (api, scraper, rss, social)"""
        query = select(SignalContract).where(SignalContract.source_type == source_type)
        if active_only:
            query = query.where(
                SignalContract.is_active.is_(True),
                SignalContract.status == "active",
            )
        result = await self.db.execute(
            query.order_by(SignalContract.name).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_schedule_tier(
        self,
        tier: str,
    ) -> list[SignalContract]:
        """Get active contracts by schedule tier (realtime, standard, slow, daily)"""
        result = await self.db.execute(
            select(SignalContract).where(
                SignalContract.schedule_tier == tier,
                SignalContract.is_active.is_(True),
                SignalContract.status == "active",
            )
        )
        return list(result.scalars().all())

    async def get_due_for_fetch(self, before: datetime) -> list[SignalContract]:
        """Get active contracts that haven't been fetched since `before` timestamp.

        Used by the scheduler to find contracts that need refreshing.
        """
        result = await self.db.execute(
            select(SignalContract).where(
                SignalContract.is_active.is_(True),
                SignalContract.status.in_(["active", "degraded"]),
                (
                    SignalContract.last_fetched_at.is_(None)
                    | (SignalContract.last_fetched_at < before)
                ),
            )
        )
        return list(result.scalars().all())

    async def mark_fetched(
        self,
        contract_id: UUID,
        *,
        reset_failures: bool = True,
    ) -> SignalContract | None:
        """Mark a contract as successfully fetched"""
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
        """Record a fetch failure. Degrades contract after max_failures."""
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
        self, *, skip: int = 0, limit: int = 100
    ) -> list[SignalContract]:
        """Get all degraded contracts (needing attention)"""
        result = await self.db.execute(
            select(SignalContract)
            .where(SignalContract.status == "degraded")
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
