"""Beta lifecycle service for managing beta account transitions"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.organization import Organization
from backend.repositories.beta_repository import BetaRepository


class BetaLifecycleService:
    """Service for beta account lifecycle management and notifications"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.beta_repo = BetaRepository(db)

    async def process_beta_notifications(self) -> dict:
        """
        Scheduled job: Send notifications for expiring beta accounts.
        Should run daily via cron/scheduler.

        Returns:
            Dictionary with notification counts
        """
        notifications_sent = {"14d": 0, "7d": 0}

        # 14-day warnings
        expiring_14d = await self.beta_repo.get_expiring_soon(14)
        for beta in expiring_14d:
            if not beta.notified_14d_before:
                await self._send_beta_expiry_notification(
                    beta.org_id, days_remaining=14
                )
                await self.beta_repo.mark_notified(beta.id, "14d")
                notifications_sent["14d"] += 1

        # 7-day warnings
        expiring_7d = await self.beta_repo.get_expiring_soon(7)
        for beta in expiring_7d:
            if not beta.notified_7d_before:
                await self._send_beta_expiry_notification(
                    beta.org_id, days_remaining=7
                )
                await self.beta_repo.mark_notified(beta.id, "7d")
                notifications_sent["7d"] += 1

        return notifications_sent

    async def process_beta_expirations(self) -> int:
        """
        Scheduled job: Transition expired beta accounts to standard pricing.
        Should run daily via cron/scheduler.

        Returns:
            Number of accounts transitioned
        """
        expired_accounts = await self.beta_repo.get_expired_accounts()
        transitioned_count = 0

        for beta in expired_accounts:
            # Get organization
            result = await self.db.execute(
                select(Organization).where(Organization.id == beta.org_id)
            )
            organization = result.scalar_one_or_none()

            if organization and organization.is_beta_account:
                # Transition to standard pricing
                organization.is_beta_account = False
                await self.beta_repo.mark_transitioned(beta.id)

                # Send notification about transition
                await self._send_standard_pricing_notification(organization.id)

                transitioned_count += 1

        await self.db.commit()
        return transitioned_count

    async def create_beta_account(
        self, org_id: UUID, duration_days: int, discount_percent: float = 50.0
    ):
        """
        Enroll an organization in beta pricing.

        Args:
            org_id: Organization ID
            duration_days: Length of beta period in days
            discount_percent: Discount percentage (default 50%)
        """
        from datetime import timedelta

        # Get organization
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        organization = result.scalar_one_or_none()

        if not organization:
            raise ValueError(f"Organization not found: {org_id}")

        # Update organization
        beta_start = datetime.now(timezone.utc)
        beta_end = beta_start + timedelta(days=duration_days)

        organization.is_beta_account = True
        organization.beta_start_date = beta_start
        organization.beta_end_date = beta_end
        organization.beta_discount_percent = discount_percent

        # Create beta tracking record
        await self.beta_repo.create_beta_account(
            org_id=org_id,
            beta_start_date=beta_start,
            beta_end_date=beta_end,
            discount_percent=discount_percent,
        )

        await self.db.commit()
        await self.db.refresh(organization)

        return organization

    async def extend_beta_period(self, org_id: UUID, additional_days: int):
        """
        Extend beta period for an organization.

        Args:
            org_id: Organization ID
            additional_days: Days to add to beta period
        """
        from datetime import timedelta

        beta = await self.beta_repo.get_by_org_id(org_id)
        if not beta:
            raise ValueError(f"No beta account found for organization: {org_id}")

        # Extend beta end date
        beta.beta_end_date += timedelta(days=additional_days)

        # Update organization
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        organization = result.scalar_one_or_none()

        if organization:
            organization.beta_end_date = beta.beta_end_date

        await self.db.commit()

    async def _send_beta_expiry_notification(
        self, org_id: UUID, days_remaining: int
    ):
        """
        Send email/notification about beta expiry.
        TODO: Integrate with actual notification service.

        Args:
            org_id: Organization ID
            days_remaining: Days until beta expires
        """
        # Placeholder for notification integration
        print(
            f"[BETA NOTIFICATION] Org {org_id}: Beta expires in {days_remaining} days"
        )
        # TODO: Implement actual email/notification logic
        pass

    async def _send_standard_pricing_notification(self, org_id: UUID):
        """
        Send notification about transition to standard pricing.
        TODO: Integrate with actual notification service.

        Args:
            org_id: Organization ID
        """
        # Placeholder for notification integration
        print(f"[BETA NOTIFICATION] Org {org_id}: Transitioned to standard pricing")
        # TODO: Implement actual email/notification logic
        pass
