"""Credit transaction repository"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.credit_transaction import CreditTransaction
from backend.models.organization import Organization


class CreditRepository:
    """Repository for credit consumption and tracking"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def consume_credits(
        self,
        org_id: UUID,
        user_id: UUID,
        action_type: str,
        credits: int,
        metadata: dict = None,
    ) -> CreditTransaction:
        """
        Consume credits and log transaction.
        
        Args:
            org_id: Organization ID
            user_id: User ID performing the action
            action_type: Type of action consuming credits
            credits: Number of credits to consume
            metadata: Additional context data
            
        Returns:
            CreditTransaction record
            
        Raises:
            ValueError: If organization not found
        """
        # Get organization
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()

        if not org:
            raise ValueError("Organization not found")

        # Update consumed credits (allow overage)
        org.credits_consumed += credits

        # Calculate remaining credits
        remaining = org.credits_allocated_monthly - org.credits_consumed

        # Create transaction record
        txn = CreditTransaction(
            org_id=org_id,
            user_id=user_id,
            action_type=action_type,
            credits_consumed=credits,
            credits_remaining=remaining,
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
        org = result.scalar_one_or_none()

        if not org:
            return 0

        return max(0, org.credits_allocated_monthly - org.credits_consumed)

    async def get_overage(self, org_id: UUID) -> int:
        """Get overage credits (0 if no overage)"""
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()

        if not org:
            return 0

        overage = org.credits_consumed - org.credits_allocated_monthly
        return max(0, overage)

    async def get_transactions(
        self, org_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[CreditTransaction]:
        """Get credit transaction history for organization"""
        result = await self.db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.org_id == org_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_consumption_by_action(self, org_id: UUID) -> dict[str, int]:
        """Get credit consumption breakdown by action type"""
        result = await self.db.execute(
            select(
                CreditTransaction.action_type,
                func.sum(CreditTransaction.credits_consumed).label("total"),
            )
            .where(CreditTransaction.org_id == org_id)
            .group_by(CreditTransaction.action_type)
        )

        return {row.action_type: row.total for row in result}

    async def reset_monthly_credits(self, org_id: UUID):
        """Reset consumed credits for monthly billing cycle"""
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()

        if org:
            org.credits_consumed = 0
            await self.db.commit()
