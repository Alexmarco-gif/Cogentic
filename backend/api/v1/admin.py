"""Admin API endpoints for pricing and feature management"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import require_permissions
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.repositories.pricing_repository import PricingRepository
from backend.services.beta_lifecycle_service import BetaLifecycleService
from backend.services.trial_service import TrialService

router = APIRouter(prefix="/admin")


class PricingModeResponse(BaseModel):
    """Pricing mode response"""

    mode: str


class PricingModeRequest(BaseModel):
    """Pricing mode update request"""

    mode: str


class BetaEnrollmentRequest(BaseModel):
    """Beta enrollment request"""

    org_id: str
    duration_days: int
    discount_percent: float = 50.0


class StatusModeResponse(BaseModel):
    """Response for pricing mode update."""

    status: str
    mode: str


class BetaEnrollmentResponse(BaseModel):
    """Response for beta enrollment."""

    status: str
    org_id: str
    beta_ends: str


class NotificationProcessResponse(BaseModel):
    """Response for notification processing."""

    status: str
    notifications_sent: int


class ExpirationProcessResponse(BaseModel):
    """Response for expiration/trial processing."""

    status: str
    accounts_transitioned: int | None = None
    trials_processed: int | None = None


@router.get("/pricing/mode", response_model=PricingModeResponse)
async def get_pricing_mode(
    auth: AuthContext = Depends(require_permissions(["owner", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get global pricing mode (beta or standard).

    Requires admin permissions.
    """
    pricing_repo = PricingRepository(db)
    mode = await pricing_repo.get_global_pricing_mode()

    return PricingModeResponse(mode=mode)


@router.post("/pricing/mode", response_model=StatusModeResponse)
async def set_pricing_mode(
    request: PricingModeRequest,
    auth: AuthContext = Depends(require_permissions(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Set global pricing mode (beta or standard).

    Requires owner permissions. This affects pricing for new signups.
    """
    if request.mode not in ["beta", "standard"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode must be 'beta' or 'standard'",
        )

    pricing_repo = PricingRepository(db)
    await pricing_repo.set_global_pricing_mode(request.mode, auth.user_id)

    return {"status": "updated", "mode": request.mode}


@router.post("/beta/enroll", response_model=BetaEnrollmentResponse)
async def enroll_beta_account(
    request: BetaEnrollmentRequest,
    auth: AuthContext = Depends(require_permissions(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Enroll an organization in beta pricing.

    Requires owner permissions.
    """
    from uuid import UUID

    try:
        org_id = UUID(request.org_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid organization ID"
        )

    beta_service = BetaLifecycleService(db)

    try:
        organization = await beta_service.create_beta_account(
            org_id=org_id,
            duration_days=request.duration_days,
            discount_percent=request.discount_percent,
        )

        return {
            "status": "enrolled",
            "org_id": str(org_id),
            "beta_ends": organization.beta_end_date.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/beta/process-notifications", response_model=NotificationProcessResponse)
async def process_beta_notifications(
    auth: AuthContext = Depends(require_permissions(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger beta notification processing.

    Normally runs as scheduled job. Requires owner permissions.
    """
    beta_service = BetaLifecycleService(db)
    notifications = await beta_service.process_beta_notifications()

    return {
        "status": "processed",
        "notifications_sent": notifications,
    }


@router.post("/beta/process-expirations", response_model=ExpirationProcessResponse)
async def process_beta_expirations(
    auth: AuthContext = Depends(require_permissions(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger beta expiration processing.

    Normally runs as scheduled job. Requires owner permissions.
    """
    beta_service = BetaLifecycleService(db)
    count = await beta_service.process_beta_expirations()

    return {
        "status": "processed",
        "accounts_transitioned": count,
    }


@router.post("/trials/process-expiries", response_model=ExpirationProcessResponse)
async def process_trial_expiries(
    auth: AuthContext = Depends(require_permissions(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger trial expiry processing.

    Normally runs as scheduled job. Requires owner permissions.
    """
    trial_service = TrialService(db)
    count = await trial_service.check_all_expired_trials()

    return {
        "status": "processed",
        "trials_processed": count,
    }
