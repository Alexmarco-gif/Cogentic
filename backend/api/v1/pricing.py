"""Pricing API endpoints."""

from datetime import datetime, timezone

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

router = APIRouter(prefix="/pricing")


class PricingSummaryResponse(BaseModel):
    """Pricing summary response"""

    tier: str
    standard_price: float
    subscription_price: float
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


class TierUpgradeResponse(BaseModel):
    """Tier upgrade request acknowledgement."""

    status: str
    requested_tier: str
    message: str


@router.get("/current", response_model=PricingSummaryResponse)
async def get_current_pricing(
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current subscription pricing for authenticated organization.

    Returns current subscription pricing details.
    """
    pricing_service = PricingService(db)
    summary = await pricing_service.calculate_total_monthly_cost(organization)

    return PricingSummaryResponse(
        tier=organization.pricing_tier,
        standard_price=await pricing_service.pricing_repo.get_tier_price(
            organization.pricing_tier
        ),
        subscription_price=summary["subscription_price"],
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
    and role, using the same DB-backed GatingService that protected routes use.
    """
    gating_service = GatingService(db)
    feature_map = await gating_service.get_feature_map(organization, auth.role)

    return FeatureAccessResponse(
        tier=organization.pricing_tier, role=auth.role, features=feature_map
    )


@router.post("/upgrade", response_model=TierUpgradeResponse)
async def upgrade_tier(
    request: TierUpgradeRequest,
    auth: AuthContext = Depends(require_permissions(["owner", "admin"])),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """
    Record a tier-upgrade request for billing follow-up.

    Requires owner or admin role.
    Self-serve billing is intentionally disabled until payment processing
    is implemented. This endpoint creates an auditable pending request without
    mutating the organization's live entitlements.
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

    settings = dict(organization.settings or {})
    existing_request = settings.get("pending_tier_upgrade")
    if (
        isinstance(existing_request, dict)
        and existing_request.get("target_tier") == request.target_tier
        and existing_request.get("status") == "pending"
    ):
        return TierUpgradeResponse(
            status="already_pending",
            requested_tier=request.target_tier,
            message="A billing review is already pending for this tier upgrade.",
        )

    settings["pending_tier_upgrade"] = {
        "status": "pending",
        "target_tier": request.target_tier,
        "current_tier": organization.pricing_tier,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "requested_by": str(auth.user_id),
        "requires_payment_processor": True,
    }
    organization.settings = settings
    await db.commit()

    return TierUpgradeResponse(
        status="pending_review",
        requested_tier=request.target_tier,
        message=(
            "Tier upgrade recorded. Billing activation is pending until the "
            "payment processor is enabled."
        ),
    )


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
