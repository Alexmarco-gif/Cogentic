"""Recommendations API endpoints.

Get signal recommendations and trigger batch generation.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.queue import enqueue_job
from backend.schemas.recommendations import (
    RecommendationBatchResponse,
    RecommendationEnriched,
    RecommendationListResponse,
    RecommendationResponse,
)
from backend.services.recommendation import RecommendationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommendations")


@router.get(
    "/signals/{signal_id}",
    response_model=RecommendationListResponse,
)
async def get_signal_recommendations(
    signal_id: UUID,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get recommendations for a specific signal.

    Returns related signals ranked by composite score
    (embedding similarity + entity overlap + industry alignment).
    """
    service = RecommendationService(db)
    items = await service.get_for_signal(signal_id, limit=limit)

    return RecommendationListResponse(
        items=[RecommendationEnriched(**r) for r in items],
        source_id=str(signal_id),
        source_type="signal",
    )


@router.get("/active", response_model=list[RecommendationResponse])
async def get_active_recommendations(
    source_type: str = Query("signal", pattern=r"^(signal|brief|entity)$"),
    min_score: float = Query(0.5, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get active high-scoring recommendations."""
    service = RecommendationService(db)
    recs = await service.get_active(
        source_type=source_type,
        limit=limit,
        min_score=min_score,
    )
    return [RecommendationResponse.model_validate(r) for r in recs]


@router.post(
    "/generate",
    response_model=RecommendationBatchResponse,
)
async def trigger_recommendation_batch(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Trigger batch recommendation generation.

    Enqueues an RQ job. Called after refinement pipeline or manually.
    """
    from backend.services.recommendation import run_recommendation_batch

    job = enqueue_job(
        run_recommendation_batch,
        limit,
        queue_name="low",
        job_timeout="30m",
    )

    return RecommendationBatchResponse(
        processed=0,
        recommendations=0,
        errors=0,
        duration_ms=0,
    )
