"""Credit repository for credit consumption tracking"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.credit_transaction import CreditTransaction
from backend.models.organization import Organization
from backend.repositories.base import BaseRepository


class CreditRepository(BaseRepository[CreditTransaction]):
    """Repository for credit transactions and balance management"""

    def __init__(self, db: AsyncSession):
        super().__init__(CreditTransaction, db)

    async def consume_credits(
        self,
        org_id: UUID,
        user_id: UUID | None,
        action_type: str,
        credits: int,
        metadata: dict | None = None,
    ) -> CreditTransaction:
        """
        Consume credits and log transaction.
        Allows overage (doesn't block if exceeds allocation).
        """
        # Get organization
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        organization = result.scalar_one_or_none()

        if not organization:
            raise ValueError(f"Organization not found: {org_id}")

        # Update organization credit consumption
        organization.credits_consumed += credits

        # Calculate remaining credits (can be negative in overage)
        credits_remaining = organization.credits_allocated_monthly - organization.credits_consumed

        # Create transaction record
        txn = CreditTransaction(
            org_id=org_id,
            user_id=user_id,
            action_type=action_type,
            credits_consumed=credits,
            credits_remaining=credits_remaining,
            metadata=metadata or {},
        )

        self.db.add(txn)
        await self.db.commit()
        await self.db.refresh(txn)

        return txn

    async def get_remaining_credits(self, org_id: UUID) -> int:
        """Get remaining credits for organization"""
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        organization = result.scalar_one_or_none()

        if not organization:
            return 0

        remaining = organization.credits_allocated_monthly - organization.credits_consumed
        return max(0, remaining)

    async def get_overage(self, org_id: UUID) -> int:
        """Get overage credits (returns 0 if no overage)"""
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        organization = result.scalar_one_or_none()

        if not organization:
            return 0

        overage = organization.credits_consumed - organization.credits_allocated_monthly
        return max(0, overage)

    async def get_transaction_history(
        self, org_id: UUID, limit: int = 50
    ) -> list[CreditTransaction]:
        """Get credit transaction history for an organization"""
        result = await self.db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.org_id == org_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_consumption_by_action_type(
        self, org_id: UUID, action_type: str
    ) -> int:
        """Get total credits consumed for a specific action type"""
        result = await self.db.execute(
            select(func.sum(CreditTransaction.credits_consumed))
            .where(
                CreditTransaction.org_id == org_id,
                CreditTransaction.action_type == action_type,
            )
        )
        total = result.scalar_one_or_none()
        return int(total) if total else 0

    async def reset_monthly_credits(self, org_id: UUID) -> None:
        """Reset credit consumption at start of new billing cycle"""
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        organization = result.scalar_one_or_none()

        if organization:
            organization.credits_consumed = 0
            await self.db.commit()
