"""Feedback API endpoints.

Captures user feedback to power the network-effect learning loop.
Every interaction makes the platform smarter for ALL users.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback")


# ── Schemas ──────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    feedback_type: str = Field(
        ...,
        description=(
            "One of: signal_useful, signal_not_useful, signal_saved, "
            "signal_shared, signal_dismissed, brief_helpful, brief_not_helpful, "
            "entity_relevant, entity_not_relevant, prediction_accurate, "
            "prediction_inaccurate"
        ),
    )
    target_type: str = Field(
        ..., description="One of: signal, brief, entity, prediction"
    )
    target_id: str = Field(..., description="UUID of the target object")
    comment: str | None = Field(None, max_length=1000)
    context: dict | None = None


class FeedbackResponse(BaseModel):
    id: str
    feedback_type: str
    target_type: str
    target_id: str
    sentiment: float


class SignalQualityResponse(BaseModel):
    signal_id: str
    quality_score: float
    total_votes: int
    useful_votes: int
    not_useful_votes: int
    saves: int
    shares: int


class TrendingSignalResponse(BaseModel):
    signal_id: str
    engagement_count: int
    unique_users: int
    unique_orgs: int
    virality_score: float


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Submit user feedback on a signal, brief, entity, or prediction.

    Every feedback event trains the platform's intelligence models:
      - signal_useful/not_useful → improves signal ranking for all users
      - prediction_accurate/inaccurate → tunes causal intelligence
      - entity_relevant/not_relevant → improves entity resolution
    """
    from backend.services.feedback_service import FeedbackService

    service = FeedbackService(db)
    feedback = await service.record_feedback(
        user_id=auth.user_id,
        org_id=auth.org_id,
        feedback_type=body.feedback_type,
        target_type=body.target_type,
        target_id=UUID(body.target_id),
        comment=body.comment,
        context=body.context,
    )
    await db.commit()

    return FeedbackResponse(
        id=str(feedback.id),
        feedback_type=feedback.feedback_type,
        target_type=feedback.target_type,
        target_id=str(feedback.target_id),
        sentiment=feedback.sentiment,
    )


@router.get("/signal/{signal_id}/quality", response_model=SignalQualityResponse)
async def get_signal_quality(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get aggregated quality score for a signal based on collective feedback."""
    from backend.services.feedback_service import FeedbackService

    service = FeedbackService(db)
    quality = await service.get_signal_quality_score(signal_id)

    return SignalQualityResponse(
        signal_id=quality["signal_id"],
        quality_score=quality["quality_score"],
        total_votes=quality["total_votes"],
        useful_votes=quality["useful_votes"],
        not_useful_votes=quality["not_useful_votes"],
        saves=quality["saves"],
        shares=quality["shares"],
    )


@router.get("/trending", response_model=list[TrendingSignalResponse])
async def get_trending_signals(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get signals trending by engagement across all ESIP users.

    Collective intelligence: what the community finds most valuable.
    """
    from backend.services.feedback_service import FeedbackService

    service = FeedbackService(db)
    trending = await service.get_trending_signals(
        org_id=auth.org_id,
        hours=hours,
        limit=limit,
    )
    return [TrendingSignalResponse(**t) for t in trending]


@router.get("/predictions/accuracy")
async def get_prediction_accuracy(
    lookback_days: int = Query(default=90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get overall prediction accuracy based on user validation.

    Returns accuracy rate of the causal intelligence engine based on
    user-validated predictions.
    """
    from backend.services.feedback_service import FeedbackService

    service = FeedbackService(db)
    accuracy = await service.get_prediction_accuracy(lookback_days=lookback_days)
    return accuracy


@router.get("/me/summary")
async def get_my_feedback_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get your feedback activity summary."""
    from backend.services.feedback_service import FeedbackService

    service = FeedbackService(db)
    summary = await service.get_user_feedback_summary(
        auth.user_id, days=days
    )
    return summary
