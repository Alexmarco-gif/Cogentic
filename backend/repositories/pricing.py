"""Pricing configuration repository"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.pricing_config import PricingConfig


class PricingRepository:
    """Repository for pricing configuration management"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_config(self, key: str) -> Optional[dict]:
        """Fetch pricing config value by key"""
        result = await self.db.execute(
            select(PricingConfig).where(PricingConfig.config_key == key)
        )
        config = result.scalar_one_or_none()
        return config.config_value if config else None

    async def update_config(self, key: str, value: dict, user_id: UUID):
        """Update pricing config (admin only)"""
        result = await self.db.execute(
            select(PricingConfig).where(PricingConfig.config_key == key)
        )
        config = result.scalar_one_or_none()

        if config:
            config.config_value = value
            config.updated_by = user_id
        else:
            config = PricingConfig(
                config_key=key, config_value=value, updated_by=user_id
            )
            self.db.add(config)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def get_global_pricing_mode(self) -> str:
        """Returns 'beta' or 'standard'"""
        mode = await self.get_config("global_pricing_mode")
        return mode if mode in ["beta", "standard"] else "standard"

    async def set_global_pricing_mode(self, mode: str, user_id: UUID):
        """Admin toggle for pricing mode"""
        if mode not in ["beta", "standard"]:
            raise ValueError("Invalid pricing mode")
        return await self.update_config("global_pricing_mode", mode, user_id)

    async def get_tier_price(self, tier: str) -> int:
        """Get standard price for a tier"""
        price_key = f"standard_price_{tier}"
        price = await self.get_config(price_key)
        return int(price) if price is not None else 0

    async def get_trial_config(self) -> dict:
        """Get trial configuration"""
        duration = await self.get_config("trial_duration_days")
        credits = await self.get_config("trial_credits")
        return {
            "duration_days": int(duration) if duration else 30,
            "credits": int(credits) if credits else 10000,
        }
