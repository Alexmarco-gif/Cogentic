"""Bulk Operations API - Batch endpoints for efficiency.

Reduces API round trips for common batch operations.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.middleware.feature_gating import get_current_organization, require_feature
from backend.repositories.intelligence_brief import IntelligenceBriefRepository
from backend.repositories.signal import SignalRepository
from backend.schemas.briefs import BriefResponse
from backend.schemas.signals import SignalResponse
from backend.services.credit_service import CreditService, InsufficientCreditsError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bulk")


# ── Request Schemas ──────────────────────────────────────────────────


class BulkFetchSignalsRequest(BaseModel):
    """Request to fetch multiple signals by ID."""

    signal_ids: list[UUID] = Field(
        ..., max_length=100, description="Signal IDs to fetch"
    )


class BulkFetchBriefsRequest(BaseModel):
    """Request to fetch multiple briefs by ID."""

    brief_ids: list[UUID] = Field(..., max_length=50, description="Brief IDs to fetch")


class BulkUpdateSignalRequest(BaseModel):
    """Request to update signal status in bulk."""

    signal_ids: list[UUID] = Field(..., max_length=100)
    archived: bool | None = None


# ── Response Schemas ─────────────────────────────────────────────────


class BulkSignalsResponse(BaseModel):
    """Bulk signals fetch response."""

    signals: list[SignalResponse]
    found: int
    missing: int


class BulkBriefsResponse(BaseModel):
    """Bulk briefs fetch response."""

    briefs: list[BriefResponse]
    found: int
    missing: int


class BulkUpdateResponse(BaseModel):
    """Bulk update response."""

    updated: int
    errors: int


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/signals/fetch", response_model=BulkSignalsResponse)
async def bulk_fetch_signals(
    body: BulkFetchSignalsRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
    organization=Depends(get_current_organization),
    _feature_check: bool = Depends(require_feature("api_access")),
):
    """Fetch multiple signals by ID in one request.

    Reduces round trips for dashboard/feed loading.
    Requires Growth tier or higher (API access).
    Consumes 25 credits per batch request.
    """
    if len(body.signal_ids) > 100:
        raise HTTPException(status_code=400, detail="Max 100 signals per request")

    credit_service = CreditService(db)

    try:
        await credit_service.consume_credits(
            org_id=organization.id,
            user_id=auth.user_id,
            action_type="api_batch_pull",
            credits=25,
            metadata={
                "signal_count": len(body.signal_ids),
                "endpoint": "bulk_fetch_signals",
            },
        )
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Insufficient credits for bulk signal fetch. "
                f"Requires {e.required} credits and {e.remaining} remain."
            ),
        ) from e

    repo = SignalRepository(db)
    found_signals = await repo.get_by_ids_scoped(body.signal_ids, org_id=auth.org_id)
    signal_responses = [SignalResponse.model_validate(s) for s in found_signals]

    return BulkSignalsResponse(
        signals=signal_responses,
        found=len(signal_responses),
        missing=len(body.signal_ids) - len(signal_responses),
    )


@router.post("/briefs/fetch", response_model=BulkBriefsResponse)
async def bulk_fetch_briefs(
    body: BulkFetchBriefsRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
    organization=Depends(get_current_organization),
    _feature_check: bool = Depends(require_feature("api_access")),
):
    """Fetch multiple briefs by ID in one request.

    Requires Growth tier or higher (API access).
    Consumes 25 credits per batch request.
    """
    if len(body.brief_ids) > 50:
        raise HTTPException(status_code=400, detail="Max 50 briefs per request")

    credit_service = CreditService(db)

    try:
        await credit_service.consume_credits(
            org_id=organization.id,
            user_id=auth.user_id,
            action_type="api_batch_pull",
            credits=25,
            metadata={
                "brief_count": len(body.brief_ids),
                "endpoint": "bulk_fetch_briefs",
            },
        )
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Insufficient credits for bulk brief fetch. "
                f"Requires {e.required} credits and {e.remaining} remain."
            ),
        ) from e

    repo = IntelligenceBriefRepository(db, org_id=auth.org_id, user_id=auth.user_id)
    found_briefs = await repo.get_by_ids(body.brief_ids)
    brief_responses = [BriefResponse.model_validate(b) for b in found_briefs]

    return BulkBriefsResponse(
        briefs=brief_responses,
        found=len(brief_responses),
        missing=len(body.brief_ids) - len(brief_responses),
    )


@router.patch("/signals/archive", response_model=BulkUpdateResponse)
async def bulk_archive_signals(
    body: BulkUpdateSignalRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Archive/unarchive multiple signals in bulk."""
    if len(body.signal_ids) > 100:
        raise HTTPException(status_code=400, detail="Max 100 signals per request")

    repo = SignalRepository(db)
    updated = 0
    errors = 0

    # Batch-fetch all signals in one query (org-scoped)
    signals = await repo.get_by_ids_scoped(body.signal_ids, org_id=auth.org_id)

    for signal in signals:
        try:
            if body.archived is not None and body.archived:
                await repo.soft_delete(signal.id)
                updated += 1
        except Exception as e:
            logger.error(f"Bulk archive failed for {signal.id}: {e}")
            errors += 1

    await db.commit()

    return BulkUpdateResponse(updated=updated, errors=errors)
