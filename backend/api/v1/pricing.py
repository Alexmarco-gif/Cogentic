"""Pricing and subscription billing API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user, require_permissions
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.middleware.feature_gating import get_current_organization
from backend.models.organization import Organization
from backend.repositories.pricing_repository import PricingRepository
from backend.services.gating_service import GatingService
from backend.services.paystack_service import (
    PaystackConfigurationError,
    PaystackError,
    PaystackService,
)
from backend.services.pricing_service import PricingService

router = APIRouter(prefix="/pricing")


class SubscriptionStatusResponse(BaseModel):
    """Current payment-provider subscription snapshot."""

    provider: str | None
    status: str | None
    plan_tier: str | None
    billing_cycle: str | None
    currency: str | None
    price_cents: int | None
    latest_reference: str | None
    current_period_start: str | None
    current_period_end: str | None
    canceled_at: str | None
    provider_customer_code: str | None
    provider_subscription_code: str | None
    provider_plan_code: str | None
    can_cancel: bool


class PricingSummaryResponse(BaseModel):
    """Pricing summary response."""

    tier: str
    standard_price: float
    subscription_price: float
    overage_cost: float
    total_monthly_cost: float
    subscription: SubscriptionStatusResponse | None = None


class FeatureAccessResponse(BaseModel):
    """Feature access response."""

    tier: str
    role: str
    features: dict[str, bool]


class TierUpgradeRequest(BaseModel):
    """Request to initialize a paid tier checkout."""

    target_tier: str
    callback_url: str | None = None


class TierUpgradeResponse(BaseModel):
    """Tier checkout initialization response."""

    status: str
    requested_tier: str
    message: str
    reference: str
    access_code: str | None
    authorization_url: str | None
    public_key: str | None = None


class VerifyCheckoutRequest(BaseModel):
    """Verify a completed Paystack reference."""

    reference: str = Field(..., min_length=6)


class VerifyCheckoutResponse(BaseModel):
    """Checkout verification response."""

    status: str
    tier: str
    message: str
    reference: str
    transaction_status: str | None


class CancelSubscriptionResponse(BaseModel):
    """Subscription cancellation response."""

    status: str
    message: str


@router.get("/current", response_model=PricingSummaryResponse)
async def get_current_pricing(
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Get current pricing details and active subscription snapshot."""
    pricing_service = PricingService(db)
    paystack_service = PaystackService(db)
    summary = await pricing_service.calculate_total_monthly_cost(organization)
    subscription = await paystack_service.get_subscription_snapshot(organization.id)

    return PricingSummaryResponse(
        tier=organization.pricing_tier,
        standard_price=await pricing_service.pricing_repo.get_tier_price(
            organization.pricing_tier
        ),
        subscription_price=summary["subscription_price"],
        overage_cost=summary["overage_cost"],
        total_monthly_cost=summary["total_cost"],
        subscription=SubscriptionStatusResponse(**subscription),
    )


@router.get("/features", response_model=FeatureAccessResponse)
async def get_feature_access(
    auth: AuthContext = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's tier and role-based feature access map."""
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
    """Initialize a real Paystack checkout for a tier upgrade."""
    valid_tiers = ["explorer", "growth", "mid_market", "enterprise"]
    if request.target_tier not in valid_tiers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tier")

    gating_service = GatingService(db)
    if not gating_service.can_upgrade_to(organization.pricing_tier, request.target_tier):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only upgrade to higher tiers",
        )

    paystack_service = PaystackService(db)
    try:
        checkout = await paystack_service.initialize_subscription_checkout(
            organization,
            user_id=auth.user_id,
            user_email=auth.email,
            target_tier=request.target_tier,
            callback_url=request.callback_url,
        )
    except PaystackConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PaystackError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return TierUpgradeResponse(
        status="checkout_initialized",
        requested_tier=request.target_tier,
        message="Secure Paystack checkout is ready.",
        reference=checkout["reference"],
        access_code=checkout.get("access_code"),
        authorization_url=checkout.get("authorization_url"),
        public_key=checkout.get("public_key"),
    )


@router.post("/verify", response_model=VerifyCheckoutResponse)
async def verify_checkout(
    request: VerifyCheckoutRequest,
    auth: AuthContext = Depends(require_permissions(["owner", "admin"])),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Verify a Paystack transaction and activate the purchased tier."""
    paystack_service = PaystackService(db)
    try:
        result = await paystack_service.verify_and_activate_checkout(request.reference)
    except PaystackError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if result["tier"] != organization.pricing_tier and organization.pricing_tier != "explorer":
        # The verification response should be scoped to the same org, but keep
        # the route defensive if a client replays a mismatched reference.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verified transaction does not belong to the active organization",
        )

    return VerifyCheckoutResponse(**result)


@router.get("/subscription", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest payment-provider subscription snapshot."""
    paystack_service = PaystackService(db)
    snapshot = await paystack_service.get_subscription_snapshot(organization.id)
    return SubscriptionStatusResponse(**snapshot)


@router.post("/subscription/cancel", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    auth: AuthContext = Depends(require_permissions(["owner", "admin"])),
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """Disable the current Paystack subscription."""
    _ = auth  # Explicitly keep permission check in signature.
    paystack_service = PaystackService(db)
    try:
        result = await paystack_service.cancel_subscription(organization.id)
    except PaystackError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return CancelSubscriptionResponse(**result)


@router.get("/tiers")
async def get_tier_options(db: AsyncSession = Depends(get_db)):
    """Get available pricing tiers with public plan prices."""
    pricing_repo = PricingRepository(db)
    tiers = []
    for tier in ["explorer", "growth", "mid_market", "enterprise"]:
        price = await pricing_repo.get_tier_price(tier)
        tiers.append({"tier": tier, "price": price})
    return {"tiers": tiers}
