"""Intelligence Briefs API endpoints.

CRUD, generation, regeneration, and refresh for intelligence briefs.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.briefs.generator import BriefGenerator
from backend.briefs.refresh import BriefRefreshService
from backend.database import get_db
from backend.queue import enqueue_job
from backend.repositories.intelligence_brief import IntelligenceBriefRepository
from backend.schemas.briefs import (
    BriefDetailResponse,
    BriefGenerateRequest,
    BriefGenerateResponse,
    BriefListResponse,
    BriefRefreshBatchResponse,
    BriefRefreshResponse,
    BriefRegenerateRequest,
    BriefResponse,
    BriefStatusUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/briefs")


# ── List / Read ──────────────────────────────────────────────────────


@router.get("", response_model=BriefListResponse)
async def list_briefs(
    industry_id: UUID | None = Query(None, description="Filter by industry"),
    status: str | None = Query(None, pattern=r"^(draft|published|archived)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """List intelligence briefs (global + org-specific)."""
    repo = IntelligenceBriefRepository(
        db, org_id=auth.org_id, user_id=auth.user_id
    )

    if status == "published" or status is None:
        items = await repo.get_published(
            industry_id=industry_id, skip=skip, limit=limit
        )
    else:
        items = await repo.get_by_industry(industry_id) if industry_id else []

    # Filter by status if needed (for draft/archived)
    if status and status != "published":
        items = [b for b in items if b.status == status]

    return BriefListResponse(
        items=[BriefResponse.model_validate(b) for b in items],
        total=len(items),
        skip=skip,
        limit=limit,
    )


@router.get("/{brief_id}", response_model=BriefDetailResponse)
async def get_brief(
    brief_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get a single intelligence brief with linked signals."""
    repo = IntelligenceBriefRepository(
        db, org_id=auth.org_id, user_id=auth.user_id
    )
    brief = await repo.get_with_signals(brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    return BriefDetailResponse.model_validate(brief)


# ── Generate / Regenerate ────────────────────────────────────────────


@router.post("/generate", response_model=BriefGenerateResponse)
async def generate_brief(
    body: BriefGenerateRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Generate a new intelligence brief via AI.

    If signal_ids provided → pre-built brief from specific signals.
    If empty → auto-generated brief from topic search.
    """
    generator = BriefGenerator(db)
    try:
        brief = await generator.generate_brief(
            topic=body.topic,
            industry_id=body.industry_id,
            org_id=auth.org_id,
            signal_ids=[str(s) for s in body.signal_ids] if body.signal_ids else None,
        )
        return BriefGenerateResponse(
            brief_id=brief.id,
            title=brief.title,
            status=brief.status,
            signal_count=len(brief.signal_links) if brief.signal_links else 0,
        )
    except Exception as e:
        logger.error(f"Brief generation failed: {e}")
        raise HTTPException(status_code=500, detail="Brief generation failed")


@router.post("/{brief_id}/regenerate", response_model=BriefGenerateResponse)
async def regenerate_brief(
    brief_id: UUID,
    body: BriefRegenerateRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Regenerate an existing brief with updated signals."""
    generator = BriefGenerator(db)
    repo = IntelligenceBriefRepository(
        db, org_id=auth.org_id, user_id=auth.user_id
    )

    existing = await repo.get(brief_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Brief not found")

    try:
        brief = await generator.regenerate_brief(
            brief_id=brief_id,
            signal_ids=[str(s) for s in body.signal_ids] if body.signal_ids else None,
        )
        return BriefGenerateResponse(
            brief_id=brief.id,
            title=brief.title,
            status=brief.status,
            signal_count=len(brief.signal_links) if brief.signal_links else 0,
        )
    except Exception as e:
        logger.error(f"Brief regeneration failed: {e}")
        raise HTTPException(status_code=500, detail="Brief regeneration failed")


# ── Status Update ────────────────────────────────────────────────────


@router.patch("/{brief_id}/status", response_model=BriefResponse)
async def update_brief_status(
    brief_id: UUID,
    body: BriefStatusUpdate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Publish, archive, or revert a brief to draft."""
    repo = IntelligenceBriefRepository(
        db, org_id=auth.org_id, user_id=auth.user_id
    )
    brief = await repo.get(brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    brief.status = body.status
    await db.commit()
    await db.refresh(brief)
    return BriefResponse.model_validate(brief)


# ── Refresh ──────────────────────────────────────────────────────────


@router.post("/{brief_id}/refresh", response_model=BriefRefreshResponse)
async def refresh_brief(
    brief_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Manually trigger a single brief refresh."""
    repo = IntelligenceBriefRepository(
        db, org_id=auth.org_id, user_id=auth.user_id
    )
    brief = await repo.get(brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    service = BriefRefreshService(db)
    try:
        refreshed = await service.refresh_single(brief_id)
        return BriefRefreshResponse(
            brief_id=brief_id,
            refreshed=refreshed,
            reason="Refreshed" if refreshed else "Rate-limited or no new signals",
        )
    except Exception as e:
        logger.error(f"Brief refresh failed: {e}")
        raise HTTPException(status_code=500, detail="Brief refresh failed")


@router.post("/refresh-all", response_model=BriefRefreshBatchResponse)
async def refresh_all_briefs(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Trigger batch refresh check for all published briefs.

    Enqueues an RQ job — returns immediately.
    """
    from backend.briefs.refresh import run_brief_refresh_check

    job = enqueue_job(
        run_brief_refresh_check,
        queue_name="low",
        job_timeout="15m",
    )
    return BriefRefreshBatchResponse(
        checked=0, refreshed=0, skipped=0, errors=0
    )
