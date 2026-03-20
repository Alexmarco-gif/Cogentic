"""Trial service for reverse trial management"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.organization import Organization
from backend.models.pricing_enums import PricingTier, TrialStatus
from backend.repositories.pricing_repository import PricingRepository
from backend.services.pricing_service import PricingService


class TrialService:
    """Service for trial account management and lifecycle"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.pricing_repo = PricingRepository(db)
        self.pricing_service = PricingService(db)

    async def start_trial(self, organization: Organization) -> Organization:
        """
        Initialize 30-day reverse trial with full Growth access.

        Args:
            organization: Organization to start trial for

        Returns:
            Updated organization with trial activated
        """
        # Get trial configuration
        trial_config = await self.pricing_repo.get_trial_config()

        # Set trial dates
        organization.trial_status = TrialStatus.ACTIVE.value
        organization.trial_start_date = datetime.now(timezone.utc)
        organization.trial_end_date = datetime.now(timezone.utc) + timedelta(
            days=trial_config["duration_days"]
        )

        # Grant Growth tier access during trial
        organization.pricing_tier = PricingTier.GROWTH.value

        # Allocate trial credits
        organization.credits_allocated_monthly = trial_config["credits"]
        organization.credits_consumed = 0

        await self.db.commit()
        await self.db.refresh(organization)

        return organization

    async def check_trial_expiry(self, organization: Organization) -> Organization:
        """
        Check if trial has expired and handle downgrade.

        Args:
            organization: Organization to check

        Returns:
            Updated organization (potentially downgraded)
        """
        if organization.trial_status != TrialStatus.ACTIVE.value:
            return organization

        if not organization.trial_end_date:
            return organization

        # Check if trial has expired
        if datetime.now(timezone.utc) < organization.trial_end_date.replace(
            tzinfo=timezone.utc
        ):
            return organization

        # Trial expired - check if user has subscribed
        if organization.billing_cycle_start:
            # User subscribed - convert trial
            organization.trial_status = TrialStatus.CONVERTED.value
        else:
            # No subscription - downgrade to Explorer
            organization.trial_status = TrialStatus.EXPIRED.value
            organization.pricing_tier = PricingTier.EXPLORER.value
            organization.credits_allocated_monthly = (
                await self.pricing_service.get_tier_credits(PricingTier.EXPLORER.value)
            )
            organization.credits_consumed = 0

        await self.db.commit()
        await self.db.refresh(organization)

        return organization

    async def convert_trial_to_paid(
        self, organization: Organization, selected_tier: str
    ) -> Organization:
        """
        Convert trial to paid subscription.

        Args:
            organization: Organization to convert
            selected_tier: Tier user selected for subscription

        Returns:
            Updated organization with active subscription
        """
        # Update trial status
        organization.trial_status = TrialStatus.CONVERTED.value

        # Set selected tier
        organization.pricing_tier = selected_tier

        # Set billing cycle start
        organization.billing_cycle_start = datetime.now(timezone.utc).date()

        # Allocate credits based on tier
        organization.credits_allocated_monthly = (
            await self.pricing_service.get_tier_credits(selected_tier)
        )
        organization.credits_consumed = 0  # Reset for new billing cycle

        await self.db.commit()
        await self.db.refresh(organization)

        return organization

    async def get_active_trials(self) -> list[Organization]:
        """Get all organizations with active trials"""
        result = await self.db.execute(
            select(Organization).where(
                Organization.trial_status == TrialStatus.ACTIVE.value
            )
        )
        return list(result.scalars().all())

    async def get_expiring_trials(self, days: int) -> list[Organization]:
        """Get trials expiring within N days"""
        threshold = datetime.now(timezone.utc) + timedelta(days=days)

        result = await self.db.execute(
            select(Organization).where(
                Organization.trial_status == TrialStatus.ACTIVE.value,
                Organization.trial_end_date <= threshold,
            )
        )
        return list(result.scalars().all())

    async def check_all_expired_trials(self) -> int:
        """Process all expired trials and downgrade them.

        Called by the admin /trials/process-expiries endpoint
        and by the scheduled job.

        Returns:
            Number of trials processed (downgraded or converted).
        """
        active_trials = await self.get_active_trials()
        processed = 0
        for org in active_trials:
            before_status = org.trial_status
            await self.check_trial_expiry(org)
            if org.trial_status != before_status:
                processed += 1
        return processed
