"""Pricing service for subscription price calculation"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.organization import Organization
from backend.repositories.pricing_repository import PricingRepository


class PricingService:
    """Service for pricing calculations and subscription management"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.pricing_repo = PricingRepository(db)

    async def calculate_subscription_price(self, organization: Organization) -> Decimal:
        """
        Calculate current subscription price for organization.
        Applies beta discount if applicable.
        
        Args:
            organization: Organization instance
            
        Returns:
            Monthly subscription price in USD
        """
        # Get standard price for tier
        standard_price = await self.pricing_repo.get_tier_price(
            organization.pricing_tier
        )

        # Convert to Decimal for precise calculations
        price = Decimal(str(standard_price))

        # Apply beta discount if active
        if self._is_beta_active(organization):
            discount_percent = Decimal(str(organization.beta_discount_percent))
            discount_multiplier = (Decimal("100") - discount_percent) / Decimal("100")
            price = price * discount_multiplier

        return price

    def _is_beta_active(self, organization: Organization) -> bool:
        """Check if beta pricing is currently active for this organization"""
        if not organization.is_beta_account:
            return False

        if not organization.beta_end_date:
            return False

        if datetime.now(timezone.utc) > organization.beta_end_date.replace(tzinfo=timezone.utc):
            return False

        return True

    async def calculate_overage_cost(self, organization: Organization) -> Decimal:
        """
        Calculate cost of credit overage.
        IMPORTANT: Overage is NEVER discounted (even for beta accounts).
        
        Args:
            organization: Organization instance
            
        Returns:
            Overage cost in USD
        """
        overage_credits = max(
            0, organization.credits_consumed - organization.credits_allocated_monthly
        )

        overage_rate = Decimal(str(organization.credits_overage_rate))
        return Decimal(str(overage_credits)) * overage_rate

    async def get_pricing_summary(self, organization: Organization) -> dict:
        """
        Get comprehensive pricing summary for an organization.
        
        Returns:
            Dictionary with subscription price, overage, discounts, etc.
        """
        subscription_price = await self.calculate_subscription_price(organization)
        overage_cost = await self.calculate_overage_cost(organization)
        standard_price = await self.pricing_repo.get_tier_price(
            organization.pricing_tier
        )

        return {
            "tier": organization.pricing_tier,
            "standard_price": Decimal(str(standard_price)),
            "subscription_price": subscription_price,
            "is_beta": self._is_beta_active(organization),
            "beta_discount_percent": (
                organization.beta_discount_percent if organization.is_beta_account else 0
            ),
            "beta_ends": organization.beta_end_date,
            "overage_cost": overage_cost,
            "total_monthly_cost": subscription_price + overage_cost,
        }

    async def get_tier_upgrade_options(
        self, current_tier: str
    ) -> list[dict]:
        """
        Get available tier upgrade options with pricing.
        
        Args:
            current_tier: Current pricing tier
            
        Returns:
            List of upgrade options with details
        """
        tiers = ["explorer", "growth", "mid_market", "enterprise"]
        current_index = tiers.index(current_tier) if current_tier in tiers else 0

        options = []
        for tier in tiers[current_index + 1 :]:
            price = await self.pricing_repo.get_tier_price(tier)
            options.append({"tier": tier, "price": Decimal(str(price))})

        return options
