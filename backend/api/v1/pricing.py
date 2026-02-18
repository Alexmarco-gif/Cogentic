"""Pricing API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user, require_permissions
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.middleware.feature_gating import get_current_organization
from backend.models.organization import Organization
from backend.repositories.pricing_repository import PricingRepository
from backend.services.gating_service import GatingService
from backend.services.pricing_service import PricingService
from backend.services.trial_service import TrialService

router = APIRouter(prefix="/pricing")


class PricingSummaryResponse(BaseModel):
    """Pricing summary response"""

    tier: str
    standard_price: float
    subscription_price: float
    is_beta: bool
    beta_discount_percent: float | None
    beta_ends: str | None
    overage_cost: float
    total_monthly_cost: float


class FeatureAccessResponse(BaseModel):
    """Feature access response"""

    tier: str
    role: str
    features: dict[str, bool]


class TierUpgradeRequest(BaseModel):
    """Tier upgrade request"""

    target_tier: str


@router.get("/current", response_model=PricingSummaryResponse)
async def get_current_pricing(
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current subscription pricing for authenticated organization.

    Returns pricing details including beta discount if applicable.
    """
    pricing_service = PricingService(db)
    summary = await pricing_service.calculate_total_monthly_cost(organization)

    return PricingSummaryResponse(
        tier=organization.pricing_tier,
        standard_price=await pricing_service.pricing_repo.get_tier_price(
            organization.pricing_tier
        ),
        subscription_price=summary["subscription_price"],
        is_beta=summary["is_beta"],
        beta_discount_percent=(
            float(organization.beta_discount_percent)
            if organization.is_beta_account
            else None
        ),
        beta_ends=(
            organization.beta_end_date.isoformat()
            if organization.beta_end_date
            else None
        ),
        overage_cost=summary["overage_cost"],
        total_monthly_cost=summary["total_cost"],
    )


@router.get("/features", response_model=FeatureAccessResponse)
async def get_feature_access(
    auth: AuthContext = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """
    Get tier-based feature access map with gating enforcement.

    Returns which features the user can access based on their pricing tier
    and role, using the GatingService. Different from /features which returns
    simple boolean feature flags from FeatureFlagService.
    """
    gating_service = GatingService(db)
    feature_map = await gating_service.get_feature_map(organization, auth.role)

    return FeatureAccessResponse(
        tier=organization.pricing_tier, role=auth.role, features=feature_map
    )


@router.post("/upgrade")
async def upgrade_tier(
    request: TierUpgradeRequest,
    auth: AuthContext = Depends(require_permissions(["owner", "admin"])),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """
    Upgrade organization to a higher tier.

    Requires owner or admin role.
    TODO: Integrate with payment processor (Stripe).
    """
    # Validate tier
    valid_tiers = ["explorer", "growth", "mid_market", "enterprise"]
    if request.target_tier not in valid_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tier"
        )

    # Check if upgrade (not downgrade)
    gating_service = GatingService(db)
    if not gating_service.can_upgrade_to(
        organization.pricing_tier, request.target_tier
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only upgrade to higher tiers",
        )

    # For now, directly update tier
    # TODO: Create Stripe subscription first
    trial_service = TrialService(db)

    if organization.trial_status == "active":
        # Convert trial if still active
        await trial_service.convert_trial_to_paid(organization, request.target_tier)
    else:
        # Direct upgrade
        organization.pricing_tier = request.target_tier

        # Allocate credits
        pricing_service = PricingService(db)
        organization.credits_allocated_monthly = await pricing_service.get_tier_credits(
            request.target_tier
        )

        await db.commit()
        await db.refresh(organization)

    return {
        "status": "upgraded",
        "new_tier": request.target_tier,
        "message": "Tier upgraded successfully",
    }


@router.get("/tiers")
async def get_tier_options(db: AsyncSession = Depends(get_db)):
    """
    Get available pricing tiers with details.

    Public endpoint - no authentication required.
    """
    pricing_repo = PricingRepository(db)

    tiers = []
    for tier in ["explorer", "growth", "mid_market", "enterprise"]:
        price = await pricing_repo.get_tier_price(tier)
        tiers.append({"tier": tier, "price": price})

    return {"tiers": tiers}
