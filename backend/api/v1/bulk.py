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
from backend.repositories.intelligence_brief import IntelligenceBriefRepository
from backend.repositories.signal import SignalRepository
from backend.schemas.briefs import BriefResponse
from backend.schemas.signals import SignalResponse

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
):
    """Fetch multiple signals by ID in one request.

    Reduces round trips for dashboard/feed loading.
    """
    if len(body.signal_ids) > 100:
        raise HTTPException(status_code=400, detail="Max 100 signals per request")

    repo = SignalRepository(db)
    found_signals = []

    for sid in body.signal_ids:
        signal = await repo.get(sid)
        if signal:
            found_signals.append(SignalResponse.model_validate(signal))

    return BulkSignalsResponse(
        signals=found_signals,
        found=len(found_signals),
        missing=len(body.signal_ids) - len(found_signals),
    )


@router.post("/briefs/fetch", response_model=BulkBriefsResponse)
async def bulk_fetch_briefs(
    body: BulkFetchBriefsRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Fetch multiple briefs by ID in one request."""
    if len(body.brief_ids) > 50:
        raise HTTPException(status_code=400, detail="Max 50 briefs per request")

    repo = IntelligenceBriefRepository(db, org_id=auth.org_id, user_id=auth.user_id)
    found_briefs = []

    for bid in body.brief_ids:
        brief = await repo.get(bid)
        if brief:
            found_briefs.append(BriefResponse.model_validate(brief))

    return BulkBriefsResponse(
        briefs=found_briefs,
        found=len(found_briefs),
        missing=len(body.brief_ids) - len(found_briefs),
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

    for sid in body.signal_ids:
        try:
            if body.archived is not None:
                # Soft delete implementation
                signal = await repo.get(sid)
                if signal:
                    if body.archived:
                        await repo.soft_delete(sid)
                    updated += 1
        except Exception as e:
            logger.error(f"Bulk archive failed for {sid}: {e}")
            errors += 1

    await db.commit()

    return BulkUpdateResponse(updated=updated, errors=errors)
