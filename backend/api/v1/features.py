"""Feature access API endpoints.

Provides a read-only view of the database-backed feature gate state for the
current authenticated org/user context. This is intentionally aligned with the
same gating rules used by protected routes so the frontend and backend share
one entitlement source of truth.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import AuthContext, get_current_user
from backend.database import get_db
from backend.middleware.feature_gating import get_current_organization
from backend.models.organization import Organization
from backend.services.gating_service import GatingService

router = APIRouter(prefix="/features", tags=["features"])


class FeaturesResponse(BaseModel):
    """Feature access map for the current org and role."""

    features: dict[str, bool] = Field(
        ..., description="Current feature access map derived from DB feature gates"
    )


@router.get("", response_model=FeaturesResponse)
async def list_features(
    auth: AuthContext = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """List feature access for the current user using DB-backed gate rules."""
    gating_service = GatingService(db)
    feature_map = await gating_service.get_feature_map(organization, auth.role)
    return FeaturesResponse(features=feature_map)


@router.get("/{feature_name}")
async def check_feature(
    feature_name: str,
    auth: AuthContext = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool | str]:
    """Check whether a specific DB-backed feature gate is enabled."""
    gating_service = GatingService(db)
    feature_map = await gating_service.get_feature_map(organization, auth.role)
    return {
        "feature": feature_name,
        "enabled": feature_map.get(feature_name, False),
    }
