"""Beta account repository"""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.beta_account import BetaAccount


class BetaRepository:
    """Repository for beta account lifecycle management"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_org_id(self, org_id: UUID) -> BetaAccount | None:
        """Get beta account by organization ID"""
        result = await self.db.execute(
            select(BetaAccount).where(BetaAccount.org_id == org_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self, org_id: UUID, beta_start: datetime, beta_end: datetime, discount: float = 50.00
    ) -> BetaAccount:
        """Create a new beta account record"""
        beta = BetaAccount(
            org_id=org_id,
            beta_start_date=beta_start,
            beta_end_date=beta_end,
            discount_percent=discount,
        )
        self.db.add(beta)
        await self.db.commit()
        await self.db.refresh(beta)
        return beta

    async def get_expiring_soon(self, days: int) -> list[BetaAccount]:
        """
        Get beta accounts expiring within N days.
        
        Args:
            days: Number of days ahead to check
            
        Returns:
            List of beta accounts expiring within the specified timeframe
        """
        threshold = datetime.utcnow() + timedelta(days=days)
        result = await self.db.execute(
            select(BetaAccount).where(
                BetaAccount.beta_end_date <= threshold,
                BetaAccount.transitioned_to_standard == False,
            )
        )
        return list(result.scalars().all())

    async def get_expired(self) -> list[BetaAccount]:
        """Get beta accounts that have expired but not yet transitioned"""
        result = await self.db.execute(
            select(BetaAccount).where(
                BetaAccount.beta_end_date <= datetime.utcnow(),
                BetaAccount.transitioned_to_standard == False,
            )
        )
        return list(result.scalars().all())

    async def mark_notified(self, beta_id: UUID, notification_type: str):
        """
        Mark notification as sent for beta account.
        
        Args:
            beta_id: Beta account ID
            notification_type: '14d' for 14-day warning, '7d' for 7-day warning
        """
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

    async def mark_transitioned(self, beta_id: UUID):
        """Mark beta account as transitioned to standard pricing"""
        result = await self.db.execute(
            select(BetaAccount).where(BetaAccount.id == beta_id)
        )
        beta = result.scalar_one_or_none()

        if beta:
            beta.transitioned_to_standard = True
            await self.db.commit()
