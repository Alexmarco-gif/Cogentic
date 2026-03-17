"""Pricing service for subscription price calculation"""

from decimal import Decimal

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

        Args:
            organization: Organization instance

        Returns:
            Monthly subscription price in USD
        """
        standard_price = await self.pricing_repo.get_tier_price(
            organization.pricing_tier
        )
        return Decimal(str(standard_price))

    async def calculate_overage_cost(self, organization: Organization) -> Decimal:
        """
        Calculate cost of credit overage.

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
            "overage_cost": overage_cost,
            "total_monthly_cost": subscription_price + overage_cost,
        }

    async def get_tier_upgrade_options(self, current_tier: str) -> list[dict]:
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

    async def calculate_total_monthly_cost(self, organization: Organization) -> dict:
        """
        Calculate total monthly cost including subscription and overage.

        Alias for get_pricing_summary that returns the data in the format
        expected by the pricing API endpoint.

        Args:
            organization: Organization instance

        Returns:
            Dictionary with subscription_price, overage_cost, total_cost, is_beta
        """
        subscription_price = await self.calculate_subscription_price(organization)
        overage_cost = await self.calculate_overage_cost(organization)

        return {
            "subscription_price": float(subscription_price),
            "overage_cost": float(overage_cost),
            "total_cost": float(subscription_price + overage_cost),
        }

    async def get_tier_credits(self, tier: str) -> int:
        """
        Get the monthly credit allocation for a given tier.

        Args:
            tier: Pricing tier string (explorer, growth, mid_market, enterprise)

        Returns:
            Monthly credit allocation
        """
        tier_credits = {
            "explorer": 1000,
            "growth": 5000,
            "mid_market": 25000,
            "enterprise": 100000,
        }
        return tier_credits.get(tier, 0)
