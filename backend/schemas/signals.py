"""Pydantic schemas for signal contracts and signals.

Request/response models for the signals and contracts API endpoints.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ── Signal Contract Schemas ──────────────────────────────────────────


class SignalContractBase(BaseModel):
    """Shared signal contract fields."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    source_url: str = Field(..., min_length=1)
    source_type: str = Field(..., pattern=r"^(api|scraper|rss|social)$")
    refresh_cron: str = Field(default="0 */1 * * *")
    schedule_tier: str = Field(
        default="standard",
        pattern=r"^(realtime|standard|slow|daily)$",
    )
    extraction_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class SignalContractCreate(SignalContractBase):
    """Schema for creating a new signal contract."""

    industry_id: UUID
    entity_id: UUID | None = None


class SignalContractUpdate(BaseModel):
    """Schema for updating a signal contract (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    source_url: str | None = None
    source_type: str | None = Field(None, pattern=r"^(api|scraper|rss|social)$")
    refresh_cron: str | None = None
    schedule_tier: str | None = Field(None, pattern=r"^(realtime|standard|slow|daily)$")
    extraction_config: dict[str, Any] | None = None
    is_active: bool | None = None


class SignalContractResponse(BaseModel):
    """Signal contract response."""

    id: UUID
    name: str
    description: str | None
    industry_id: UUID
    entity_id: UUID | None
    source_url: str
    source_type: str
    refresh_cron: str
    schedule_tier: str
    extraction_config: dict[str, Any]
    is_active: bool
    status: str
    failure_count: int
    max_failures: int
    last_fetched_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SignalContractListResponse(BaseModel):
    """Paginated list of signal contracts."""

    items: list[SignalContractResponse]
    total: int
    skip: int
    limit: int


# ── Signal Schemas ───────────────────────────────────────────────────


class SignalResponse(BaseModel):
    """Signal response schema."""

    id: UUID
    contract_id: UUID
    org_id: UUID | None
    title: str | None
    summary: str | None
    source_url: str | None
    signal_type: str
    confidence: float
    content_hash: str | None
    fetched_at: datetime
    published_at: datetime | None
    expires_at: datetime | None
    extracted_data: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalDetailResponse(SignalResponse):
    """Full signal detail including raw content."""

    raw_content: str | None


class SignalListResponse(BaseModel):
    """Paginated list of signals."""

    items: list[SignalResponse]
    total: int
    skip: int
    limit: int


class SignalFeedQuery(BaseModel):
    """Query parameters for signal feed."""

    industry_id: UUID | None = None
    signal_type: str | None = None
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)


# ── Job / Pipeline Schemas ───────────────────────────────────────────


class FetchContractRequest(BaseModel):
    """Request to trigger on-demand fetch for a contract."""

    contract_id: UUID


class FetchTierRequest(BaseModel):
    """Request to trigger fetch for all contracts in a tier."""

    tier: str = Field(..., pattern=r"^(realtime|standard|slow|daily)$")


class PipelineStatusResponse(BaseModel):
    """Pipeline/scheduler status response."""

    scheduler_running: bool
    active_contracts: int
    degraded_contracts: int
    degraded_names: list[str]
