"""Beta account repository for beta lifecycle management"""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.beta_account import BetaAccount
from backend.repositories.base import BaseRepository


class BetaRepository(BaseRepository[BetaAccount]):
    """Repository for beta account lifecycle tracking"""

    def __init__(self, db: AsyncSession):
        super().__init__(BetaAccount, db)

    async def get_by_org_id(self, org_id: UUID) -> BetaAccount | None:
        """Get beta account record by organization ID"""
        result = await self.db.execute(
            select(BetaAccount).where(BetaAccount.org_id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_expiring_soon(self, days: int) -> list[BetaAccount]:
        """
        Get beta accounts expiring within N days.
        Only returns accounts that haven't transitioned yet.
        """
        threshold = datetime.utcnow() + timedelta(days=days)

        result = await self.db.execute(
            select(BetaAccount).where(
                BetaAccount.beta_end_date <= threshold,
                BetaAccount.transitioned_to_standard == False,
            )
        )
        return list(result.scalars().all())

    async def get_expired_accounts(self) -> list[BetaAccount]:
        """Get all beta accounts that have expired but not transitioned"""
        result = await self.db.execute(
            select(BetaAccount).where(
                BetaAccount.beta_end_date <= datetime.utcnow(),
                BetaAccount.transitioned_to_standard == False,
            )
        )
        return list(result.scalars().all())

    async def mark_notified(self, beta_id: UUID, notification_type: str) -> None:
        """Mark notification as sent (14d or 7d)"""
        result = await self.db.execute(
            select(BetaAccount).where(BetaAccount.id == beta_id)
        )
        beta = result.scalar_one_or_none()

        if beta:
            if notification_type == "14d":
                beta.notified_14d_before = True
            elif notification_type == "7d":
                beta.notified_7d_before = True
            
            await self.db.commit()

    async def mark_transitioned(self, beta_id: UUID) -> None:
        """Mark beta account as transitioned to standard pricing"""
        result = await self.db.execute(
            select(BetaAccount).where(BetaAccount.id == beta_id)
        )
        beta = result.scalar_one_or_none()

        if beta:
            beta.transitioned_to_standard = True
            await self.db.commit()

    async def create_beta_account(
        self,
        org_id: UUID,
        beta_start_date: datetime,
        beta_end_date: datetime,
        discount_percent: float = 50.0,
    ) -> BetaAccount:
        """Create a new beta account record"""
        beta = BetaAccount(
            org_id=org_id,
            beta_start_date=beta_start_date,
            beta_end_date=beta_end_date,
            discount_percent=discount_percent,
        )

        self.db.add(beta)
        await self.db.commit()
        await self.db.refresh(beta)

        return beta
