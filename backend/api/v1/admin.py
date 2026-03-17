"""Admin API endpoints for pricing and feature management"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import require_permissions
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.repositories.pricing_repository import PricingRepository
from backend.services.trial_service import TrialService

router = APIRouter(prefix="/admin")


class PricingModeResponse(BaseModel):
    """Pricing mode response"""

    mode: str


class PricingModeRequest(BaseModel):
    """Pricing mode update request"""

    mode: str


class StatusModeResponse(BaseModel):
    """Response for pricing mode update."""

    status: str
    mode: str


class ExpirationProcessResponse(BaseModel):
    """Response for expiration/trial processing."""

    status: str
    trials_processed: int | None = None


@router.get("/pricing/mode", response_model=PricingModeResponse)
async def get_pricing_mode(
    auth: AuthContext = Depends(require_permissions(["owner", "admin"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get global pricing mode.

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
    Set global pricing mode.

    Requires owner permissions. This affects pricing for new signups.
    """
    if request.mode not in ["standard"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode must be 'standard'",
        )

    pricing_repo = PricingRepository(db)
    await pricing_repo.set_global_pricing_mode(request.mode, auth.user_id)

    return {"status": "updated", "mode": request.mode}


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
