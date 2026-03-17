"""Credit service for credit consumption tracking"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.credit_transaction import CreditTransaction
from backend.models.organization import Organization
from backend.repositories.credit_repository import CreditRepository


class CreditService:
    """Service for credit consumption and balance management"""

    # Credit costs for various actions
    CREDIT_COSTS = {
        "intelligence_brief": 50,
        "on_demand_synthesis": 100,
        "api_batch_pull": 25,
        "deep_historical_query": 200,
        "alert_trigger": 1,
        "signal_view": 0,  # Free
        "deep_search": 10,
        "deep_search_synthesis": 25,
        "document_export": 5,
        "contract_create": 25,
        "contract_manual_fetch": 25,
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.credit_repo = CreditRepository(db)

    async def consume_credits_atomic(
        self,
        org_id: UUID,
        user_id: UUID | None,
        action_type: str,
        credits: int | None = None,
        metadata: dict | None = None,
    ) -> CreditTransaction | None:
        """
        Atomically check and consume credits using SELECT ... FOR UPDATE.

        Prevents race conditions where concurrent requests both pass the
        credit check before either has decremented the balance.

        Args:
            org_id: Organization ID
            user_id: User performing action
            action_type: Type of action
            credits: Number of credits (if None, uses default for action_type)
            metadata: Additional context

        Returns:
            CreditTransaction if successful, None if insufficient credits
        """
        if credits is None:
            credits = self.CREDIT_COSTS.get(action_type, 0)

        if credits == 0:
            # Free action — no transaction needed
            return await self._record_transaction(
                org_id, user_id, action_type, 0, metadata
            )

        # Atomic: lock the org row, check balance, decrement
        result = await self.db.execute(
            select(Organization)
            .where(Organization.id == org_id)
            .with_for_update()
        )
        org = result.scalar_one_or_none()

        if not org:
            raise ValueError(f"Organization not found: {org_id}")

        remaining = org.credits_allocated_monthly - org.credits_consumed
        if remaining < credits:
            return None  # Insufficient credits

        org.credits_consumed += credits
        credits_remaining = org.credits_allocated_monthly - org.credits_consumed

        txn = CreditTransaction(
            org_id=org_id,
            user_id=user_id,
            action_type=action_type,
            credits_consumed=credits,
            credits_remaining=credits_remaining,
            metadata=metadata or {},
        )
        self.db.add(txn)
        await self.db.flush()
        await self.db.refresh(txn)
        return txn

    async def consume_credits(
        self,
        org_id: UUID,
        user_id: UUID | None,
        action_type: str,
        credits: int | None = None,
        metadata: dict | None = None,
    ) -> CreditTransaction:
        """
        Consume credits for an action.

        Args:
            org_id: Organization ID
            user_id: User ID performing action
            action_type: Type of action
            credits: Number of credits (if None, uses default for action_type)
            metadata: Additional context

        Returns:
            CreditTransaction record
        """
        # Use default credit cost if not specified
        if credits is None:
            credits = self.CREDIT_COSTS.get(action_type, 0)

        # Consume credits via repository
        return await self.credit_repo.consume_credits(
            org_id=org_id,
            user_id=user_id,
            action_type=action_type,
            credits=credits,
            metadata=metadata,
        )

    async def _record_transaction(
        self,
        org_id: UUID,
        user_id: UUID | None,
        action_type: str,
        credits: int,
        metadata: dict | None,
    ) -> CreditTransaction:
        """Record a zero-cost transaction (e.g., free actions)."""
        remaining = await self.credit_repo.get_remaining_credits(org_id)
        txn = CreditTransaction(
            org_id=org_id,
            user_id=user_id,
            action_type=action_type,
            credits_consumed=credits,
            credits_remaining=remaining,
            metadata=metadata or {},
        )
        self.db.add(txn)
        await self.db.flush()
        await self.db.refresh(txn)
        return txn

    async def get_credit_balance(self, org_id: UUID) -> dict:
        """
        Get credit balance summary for organization.

        Args:
            org_id: Organization ID

        Returns:
            Dictionary with credit allocation, consumption, and remaining
        """
        from sqlalchemy import select

        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        organization = result.scalar_one_or_none()

        if not organization:
            raise ValueError(f"Organization not found: {org_id}")

        remaining = await self.credit_repo.get_remaining_credits(org_id)
        overage = await self.credit_repo.get_overage(org_id)

        return {
            "allocated": organization.credits_allocated_monthly,
            "consumed": organization.credits_consumed,
            "remaining": remaining,
            "overage": overage,
            "overage_rate": float(organization.credits_overage_rate),
        }

    async def check_sufficient_credits(
        self, org_id: UUID, action_type: str, required_credits: int | None = None
    ) -> bool:
        """
        Check if organization has sufficient credits.
        Note: This doesn't block - overage is allowed, but we return False to warn.

        Args:
            org_id: Organization ID
            action_type: Type of action
            required_credits: Required credits (if None, uses default)

        Returns:
            True if sufficient, False if would cause overage
        """
        if required_credits is None:
            required_credits = self.CREDIT_COSTS.get(action_type, 0)

        remaining = await self.credit_repo.get_remaining_credits(org_id)
        return remaining >= required_credits

    async def get_transaction_history(
        self, org_id: UUID, limit: int = 50
    ) -> list[CreditTransaction]:
        """Get credit transaction history"""
        return await self.credit_repo.get_transaction_history(org_id, limit)

    async def reset_monthly_credits(self, org_id: UUID) -> None:
        """Reset credit consumption for new billing cycle"""
        await self.credit_repo.reset_monthly_credits(org_id)

    def get_action_credit_cost(self, action_type: str) -> int:
        """Get credit cost for an action type"""
        return self.CREDIT_COSTS.get(action_type, 0)
