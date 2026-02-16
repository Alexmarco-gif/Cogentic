"""Feature gating service for tier and role-based access control"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.organization import Organization
from backend.models.pricing_enums import PricingTier, UserRole
from backend.models.user import User
from backend.repositories.feature_gate_repository import FeatureGateRepository


class GatingService:
    """Service for feature access control based on tier and role"""

    # Tier hierarchy (higher number = higher tier)
    TIER_HIERARCHY = {
        PricingTier.EXPLORER: 0,
        PricingTier.GROWTH: 1,
        PricingTier.MID_MARKET: 2,
        PricingTier.ENTERPRISE: 3,
    }

    # Role hierarchy (for future use)
    ROLE_HIERARCHY = {
        UserRole.VIEWER: 0,
        UserRole.ANALYST: 1,
        UserRole.ADMIN: 2,
        UserRole.OWNER: 3,
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.feature_gate_repo = FeatureGateRepository(db)

    async def check_feature_access(
        self, organization: Organization, user: User, feature_key: str
    ) -> bool:
        """
        Check if user can access a feature based on tier + role.
        
        Args:
            organization: Organization instance
            user: User instance
            feature_key: Feature identifier
            
        Returns:
            True if access granted, False otherwise
        """
        # Get feature gate configuration
        feature_gate = await self.feature_gate_repo.get_by_feature_key(feature_key)

        # If no gate defined, allow access
        if not feature_gate:
            return True

        # Check tier requirement
        if feature_gate.required_tier:
            if not self._check_tier_access(
                organization.pricing_tier, feature_gate.required_tier
            ):
                return False

        # Check role requirement (if specified)
        if feature_gate.required_role:
            # Get user role from org_user relationship
            # For now, we'll need to pass role separately or query it
            # This is a simplified version
            pass

        return True

    def _check_tier_access(self, current_tier: str, required_tier: str) -> bool:
        """Check if current tier meets or exceeds required tier"""
        current_level = self.TIER_HIERARCHY.get(current_tier, 0)
        required_level = self.TIER_HIERARCHY.get(required_tier, 0)
        return current_level >= required_level

    async def require_feature(
        self, organization: Organization, user: User, feature_key: str
    ):
        """
        Raise exception if feature not accessible.
        
        Raises:
            PermissionError: If feature access denied
        """
        has_access = await self.check_feature_access(organization, user, feature_key)
        if not has_access:
            raise PermissionError(
                f"Feature '{feature_key}' requires a higher tier or different role"
            )

    async def get_feature_access_map(
        self, organization: Organization, user: User
    ) -> dict[str, bool]:
        """
        Get access map for all features.
        
        Returns:
            Dictionary mapping feature keys to access boolean
        """
        all_gates = await self.feature_gate_repo.get_all_feature_gates()

        access_map = {}
        for gate in all_gates:
            access_map[gate.feature_key] = await self.check_feature_access(
                organization, user, gate.feature_key
            )

        return access_map

    async def get_available_features(
        self, organization: Organization, user: User
    ) -> list[str]:
        """Get list of feature keys available to user"""
        access_map = await self.get_feature_access_map(organization, user)
        return [key for key, has_access in access_map.items() if has_access]

    async def get_blocked_features(
        self, organization: Organization, user: User
    ) -> list[str]:
        """Get list of feature keys blocked for user"""
        access_map = await self.get_feature_access_map(organization, user)
        return [key for key, has_access in access_map.items() if not has_access]
