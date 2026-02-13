"""Pydantic schemas for Intelligence Briefs.

Request/response models for brief CRUD, generation, and refresh endpoints.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ── Brief Response Schemas ───────────────────────────────────────────


class BriefSignalLink(BaseModel):
    """Signal linked to a brief with relevance ranking."""

    signal_id: UUID
    relevance_rank: int

    model_config = {"from_attributes": True}


class BriefResponse(BaseModel):
    """Intelligence brief response."""

    id: UUID
    org_id: UUID | None
    industry_id: UUID
    title: str
    brief_type: str
    bluf: str | None
    body_json: dict[str, Any]
    outlook: str | None
    decision_lens: str | None
    status: str
    refreshed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BriefDetailResponse(BriefResponse):
    """Brief detail including linked signals."""

    signal_links: list[BriefSignalLink] = Field(default_factory=list)


class BriefListResponse(BaseModel):
    """Paginated list of briefs."""

    items: list[BriefResponse]
    total: int
    skip: int
    limit: int


# ── Brief Generation Schemas ────────────────────────────────────────


class BriefGenerateRequest(BaseModel):
    """Request to generate a new intelligence brief."""

    topic: str = Field(..., min_length=5, max_length=500, description="Brief topic")
    industry_id: UUID = Field(..., description="Target industry")
    signal_ids: list[UUID] = Field(
        default_factory=list,
        max_length=20,
        description="Specific signals to base the brief on (empty = auto-search)",
    )


class BriefRegenerateRequest(BaseModel):
    """Request to regenerate an existing brief."""

    signal_ids: list[UUID] = Field(
        default_factory=list,
        max_length=20,
        description="Override signal IDs (empty = keep existing)",
    )


class BriefGenerateResponse(BaseModel):
    """Brief generation job result."""

    brief_id: UUID
    title: str
    status: str
    signal_count: int


# ── Brief Refresh Schemas ───────────────────────────────────────────


class BriefRefreshResponse(BaseModel):
    """Brief refresh result."""

    brief_id: UUID
    refreshed: bool
    reason: str | None = None


class BriefRefreshBatchResponse(BaseModel):
    """Batch refresh result."""

    checked: int
    refreshed: int
    skipped: int
    errors: int


# ── Brief Update Schemas ────────────────────────────────────────────


class BriefStatusUpdate(BaseModel):
    """Update brief status (publish, archive)."""

    status: str = Field(..., pattern=r"^(draft|published|archived)$")
