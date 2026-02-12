"""Pydantic schemas for Recommendations.

Response models for recommendation endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RecommendationResponse(BaseModel):
    """Individual recommendation."""

    id: UUID
    source_type: str
    source_id: UUID
    target_type: str
    target_id: UUID
    score: float
    reason: str | None
    algorithm_version: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecommendationEnriched(BaseModel):
    """Recommendation enriched with target signal details."""

    id: str
    target_id: str
    target_type: str
    score: float
    reason: str | None
    algorithm_version: str | None
    target_title: str | None
    target_signal_type: str | None
    target_confidence: float | None
    created_at: str


class RecommendationListResponse(BaseModel):
    """List of recommendations."""

    items: list[RecommendationEnriched]
    source_id: str
    source_type: str


class RecommendationBatchResponse(BaseModel):
    """Batch recommendation generation result."""

    processed: int
    recommendations: int
    errors: int
    duration_ms: int
