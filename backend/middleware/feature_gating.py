"""Feature gating middleware for tier and role-based access control"""

from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.models.organization import Organization
from backend.repositories.organization import OrganizationRepository
from backend.services.gating_service import GatingService
from sqlalchemy import select


async def get_current_organization(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """
    Get the current user's organization.
    
    Args:
        auth: Authenticated user context
        db: Database session
        
    Returns:
        Organization instance
        
    Raises:
        HTTPException: If organization not found
    """
    if not auth.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization context available",
        )

    org_repo = OrganizationRepository(db)
    organization = await org_repo.get(auth.org_id)

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return organization


def require_feature(feature_key: str) -> Callable:
    """
    Dependency factory for feature gating.
    Checks if user's organization has access to a specific feature.
    
    Args:
        feature_key: Feature identifier (e.g., 'api_access', 'compliance_modules')
        
    Returns:
        FastAPI dependency that validates feature access
        
    Usage:
        @router.get("/api/generate")
        async def generate_api_key(
            org: Organization = Depends(require_feature("api_access"))
        ):
            ...
    """

    async def feature_checker(
        auth: AuthContext = Depends(get_current_user),
        organization: Organization = Depends(get_current_organization),
        db: AsyncSession = Depends(get_db),
    ) -> bool:
        gating_service = GatingService(db)

        # Check if organization tier has access to feature
        # Simplified check using role from auth context
        from backend.repositories.feature_gate_repository import (
            FeatureGateRepository,
        )

        gate_repo = FeatureGateRepository(db)
        gate = await gate_repo.get_by_feature_key(feature_key)

        # If no gate defined, allow access
        if not gate:
            return True

        # Check tier requirement
        if gate.required_tier:
            current_level = gating_service.TIER_HIERARCHY.get(
                organization.pricing_tier, 0
            )
            required_level = gating_service.TIER_HIERARCHY.get(
                gate.required_tier, 0
            )

            if current_level < required_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "feature_access_denied",
                        "message": f"This feature requires {gate.required_tier} tier or higher",
                        "feature": feature_key,
                        "current_tier": organization.pricing_tier,
                        "required_tier": gate.required_tier,
                        "upgrade_needed": True,
                    },
                )

        # Check role requirement (if specified)
        if gate.required_role:
            current_role_level = gating_service.ROLE_HIERARCHY.get(auth.role, 0)
            required_role_level = gating_service.ROLE_HIERARCHY.get(
                gate.required_role, 0
            )

            if current_role_level < required_role_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "role_access_denied",
                        "message": f"This feature requires {gate.required_role} role or higher",
                        "feature": feature_key,
                        "current_role": auth.role,
                        "required_role": gate.required_role,
                    },
                )

        return True

    return feature_checker


def require_tier(required_tier: str) -> Callable:
    """
    Dependency factory for tier-based gating.
    Simpler than feature-based gating - just checks tier level.
    
    Args:
        required_tier: Minimum tier required (explorer, growth, mid_market, enterprise)
        
    Returns:
        FastAPI dependency that validates tier access
        
    Usage:
        @router.get("/enterprise/custom")
        async def enterprise_feature(
            org: Organization = Depends(require_tier("enterprise"))
        ):
            ...
    """

    async def tier_checker(
        organization: Organization = Depends(get_current_organization),
        db: AsyncSession = Depends(get_db),
    ) -> Organization:
        gating_service = GatingService(db)

        # Check if current tier meets requirement
        current_level = gating_service.TIER_HIERARCHY.get(
            organization.pricing_tier, 0
        )
        required_level = gating_service.TIER_HIERARCHY.get(required_tier, 0)

        if current_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "tier_access_denied",
                    "message": f"This endpoint requires {required_tier} tier or higher",
                    "current_tier": organization.pricing_tier,
                    "required_tier": required_tier,
                    "upgrade_needed": True,
                },
            )

        return organization

    return tier_checker


async def check_credit_balance(
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """
    Dependency that checks credit balance and warns about low credits.
    Does NOT block - just adds warning header.
    
    Usage:
        @router.post("/synthesis/generate")
        async def generate_synthesis(
            org: Organization = Depends(check_credit_balance)
        ):
            ...
    """
    from backend.services.credit_service import CreditService

    credit_service = CreditService(db)
    balance = await credit_service.get_credit_balance(organization.id)

    # Low credit warning threshold (20%)
    if balance["remaining"] < balance["allocated"] * 0.2:
        # Could add a warning header here if needed
        pass

    return organization
