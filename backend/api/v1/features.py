"""
Feature Flags API Endpoints

Provides API endpoints for querying available features and their status.
Useful for frontend feature detection and debugging.
"""

from typing import Dict, List
from fastapi import APIRouter, Depends

from backend.auth import get_current_user, AuthContext
from backend.services.feature_flags import FeatureFlagService, get_feature_flags_service
from pydantic import BaseModel, Field

router = APIRouter(prefix="/features", tags=["features"])


class FeatureInfo(BaseModel):
    """Information about a feature flag"""

    name: str
    enabled: bool
    description: str
    required_plan: str | None = None


class FeaturesResponse(BaseModel):
    """Response containing all features and their status"""

    enabled_features: List[str] = Field(
        ..., description="List of enabled feature names"
    )
    all_features: Dict[str, FeatureInfo] = Field(
        ..., description="All features with details"
    )


@router.get("", response_model=FeaturesResponse)
async def list_features(
    auth: AuthContext = Depends(get_current_user),
    flags: FeatureFlagService = Depends(get_feature_flags_service),
):
    """
    List all features and their status for current user.

    Returns which features are enabled for the authenticated user
    based on their plan, org, and any user-specific overrides.

    Useful for:
    - Frontend feature detection
    - Debugging feature access
    - Understanding available capabilities
    """
    # Get enabled features for this user's context
    enabled = flags.get_enabled_features(
        user_id=str(auth.user_id),
        org_id=str(auth.org_id),
        plan=auth.plan,
    )

    # Get all feature definitions
    all_features_dict = flags.list_features()

    # Build response
    all_features = {}
    for name, definition in all_features_dict.items():
        all_features[name] = FeatureInfo(
            name=name,
            enabled=name in enabled,
            description=definition.description,
            required_plan=definition.required_plan,
        )

    return FeaturesResponse(
        enabled_features=enabled,
        all_features=all_features,
    )


@router.get("/{feature_name}")
async def check_feature(
    feature_name: str,
    auth: AuthContext = Depends(get_current_user),
    flags: FeatureFlagService = Depends(get_feature_flags_service),
) -> Dict[str, bool]:
    """
    Check if a specific feature is enabled for current user.

    Returns:
        {"enabled": true/false}
    """
    enabled = flags.is_enabled(
        feature_name,
        user_id=str(auth.user_id),
        org_id=str(auth.org_id),
        plan=auth.plan,
    )

    return {"enabled": enabled}
