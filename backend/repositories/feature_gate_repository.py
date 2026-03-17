"""Feature gate repository for database-driven feature flags"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.feature_gate import FeatureGate
from backend.repositories.base import BaseRepository


class FeatureGateRepository(BaseRepository[FeatureGate]):
    """Repository for feature gate configuration"""

    def __init__(self, db: AsyncSession):
        super().__init__(FeatureGate, db)

    async def get_by_feature_key(self, feature_key: str) -> FeatureGate | None:
        """Get feature gate configuration by feature key"""
        result = await self.db.execute(
            select(FeatureGate).where(FeatureGate.feature_key == feature_key)
        )
        return result.scalar_one_or_none()

    async def get_all_feature_gates(self) -> list[FeatureGate]:
        """Get all feature gate configurations"""
        result = await self.db.execute(select(FeatureGate))
        return list(result.scalars().all())

    async def get_features_by_tier(self, tier: str) -> list[FeatureGate]:
        """Get all features available for a specific tier"""
        result = await self.db.execute(
            select(FeatureGate).where(FeatureGate.required_tier == tier)
        )
        return list(result.scalars().all())

    async def get_enterprise_only_features(self) -> list[FeatureGate]:
        """Get all enterprise-only features"""
        result = await self.db.execute(
            select(FeatureGate).where(FeatureGate.is_enterprise_only == True)
        )
        return list(result.scalars().all())
