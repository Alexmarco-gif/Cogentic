"""Pydantic schemas for Deep Live Search.

Request/response models for search execution and history endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ── Search Request/Response ──────────────────────────────────────────


class SearchRequest(BaseModel):
    """Deep search execution request."""

    query: str = Field(..., min_length=3, max_length=2000, description="Search query")
    max_results: int = Field(default=20, ge=1, le=100, description="Max results")
    min_confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum signal confidence"
    )
    include_synthesis: bool = Field(
        default=True, description="Include AI synthesis of results"
    )


class SearchResultItem(BaseModel):
    """Individual search result."""

    signal_id: str
    title: str | None
    summary: str | None
    signal_type: str | None
    confidence: float
    similarity: float
    freshness_score: float
    composite_score: float
    source_url: str | None = None
    published_at: datetime | None = None


class SearchResponse(BaseModel):
    """Deep search response."""

    query: str
    results: list[SearchResultItem]
    synthesis: str | None = None
    total_results: int
    response_time_ms: int
    cached: bool = False


# ── Search History ───────────────────────────────────────────────────


class SearchHistoryItem(BaseModel):
    """Search history entry."""

    id: UUID
    query_text: str
    source_count: int
    response_time_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchHistoryResponse(BaseModel):
    """Paginated search history."""

    items: list[SearchHistoryItem]
    total: int
    skip: int
    limit: int
