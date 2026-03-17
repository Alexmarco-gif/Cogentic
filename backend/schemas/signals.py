"""Pydantic schemas for signal contracts and signals.

Request/response models for the signals and contracts API endpoints.
"""

from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import re

from pydantic import BaseModel, Field, field_validator, model_validator

# Basic 5-field cron expression validator (covers *, n, */n, n-m, n,m per field)
_CRON_RE = re.compile(
    r"^(\*|[0-9,\-*/]+)\s+(\*|[0-9,\-*/]+)\s+(\*|[0-9,\-*/]+)\s+(\*|[0-9,\-*/]+)\s+(\*|[0-9,\-*/]+)$"
)

# Private hostnames/IPs that must never be targets of an outbound webhook.
_BLOCKED_WEBHOOK_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "[::1]",
    "metadata.google.internal",
}


def _assert_webhook_url(url: str, field_name: str = "source_url") -> None:
    """Raise ValueError when *url* is not a safe outbound webhook target.

    Performs a static scheme + hostname check only.  The full DNS-based SSRF
    guard that calls ``socket.getaddrinfo`` runs at delivery time inside
    ``send_webhook_notification()``.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValueError(f"{field_name} is not a valid URL")
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"{field_name} must use http or https scheme for webhook delivery"
        )
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError(f"{field_name} must include a hostname")
    if hostname in _BLOCKED_WEBHOOK_HOSTS:
        raise ValueError(
            f"{field_name} targets a blocked/internal host and cannot be used for webhook delivery"
        )


# ── Signal Contract Schemas ──────────────────────────────────────────


class SignalContractBase(BaseModel):
    """Shared signal contract fields."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    source_url: str = Field(..., min_length=1)
    source_type: str = Field(..., pattern=r"^(api|scraper|rss|social|webhook)$")
    refresh_cron: str = Field(default="0 */1 * * *")
    schedule_tier: str = Field(
        default="standard",
        pattern=r"^(realtime|standard|slow|daily)$",
    )
    extraction_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @field_validator("refresh_cron")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        if not _CRON_RE.match(v.strip()):
            raise ValueError(
                "refresh_cron must be a valid 5-field cron expression (e.g. '0 */1 * * *')"
            )
        return v


class SignalContractCreate(SignalContractBase):
    """Schema for creating a new signal contract."""

    industry_id: UUID
    entity_id: UUID | None = None

    @model_validator(mode="after")
    def validate_webhook_url(self) -> "SignalContractCreate":
        if self.source_type == "webhook":
            _assert_webhook_url(self.source_url)
        return self


class SignalContractUpdate(BaseModel):
    """Schema for updating a signal contract (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    source_url: str | None = None
    source_type: str | None = Field(None, pattern=r"^(api|scraper|rss|social|webhook)$")
    refresh_cron: str | None = None
    schedule_tier: str | None = Field(None, pattern=r"^(realtime|standard|slow|daily)$")
    extraction_config: dict[str, Any] | None = None
    is_active: bool | None = None

    @field_validator("refresh_cron")
    @classmethod
    def validate_cron(cls, v: str | None) -> str | None:
        if v is not None and not _CRON_RE.match(v.strip()):
            raise ValueError(
                "refresh_cron must be a valid 5-field cron expression (e.g. '0 */1 * * *')"
            )
        return v

    @model_validator(mode="after")
    def validate_webhook_url(self) -> "SignalContractUpdate":
        if self.source_type == "webhook" and self.source_url is not None:
            _assert_webhook_url(self.source_url)
        return self


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


class SignalProvenanceResponse(BaseModel):
    """Structured provenance + lineage for a signal."""

    pipeline_version: str | None = None
    ner_model: str | None = None
    ner_tokens: int = 0
    country_context: str | None = None
    entities_found: int = 0
    numeric_data_found: int = 0
    sources_found: int = 0
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    stages: dict[str, Any] = Field(default_factory=dict)
    refined_at: float | None = None


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
    # Versioning & lineage
    version: int = 1
    superseded_by_id: UUID | None = None
    amended_at: datetime | None = None
    # Provenance (populated after refinement pipeline)
    provenance: SignalProvenanceResponse | None = None
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


class IntelligenceSignalResponse(SignalResponse):
    """Signal enriched with aggregated intelligence metadata.

    Returned by /signals/feed/intelligence — combines signal data with
    ML scores, top causal prediction, and regulatory flag in one response
    to avoid N+1 queries on the frontend.
    """

    # Top ML score values (from signal_scores table)
    anomaly_score: float | None = None
    trending_score: float | None = None

    # Top entities extracted by NER (first 5 for display)
    top_entities: list[dict[str, Any]] = Field(default_factory=list)

    # Causal intelligence summary (if available)
    causal_summary: str | None = None
    causal_event_type: str | None = None

    # Regulatory flag (if a regulatory event was detected)
    regulatory_flag: str | None = None
    regulatory_body: str | None = None

    # Geographic focus (primary country/region from NER)
    primary_country: str | None = None
    primary_region: str | None = None


class SignalFeedQuery(BaseModel):
    """Query parameters for signal feed."""

    industry_id: UUID | None = None
    signal_type: str | None = None
    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)
    country: str | None = None  # ISO 3166-1 alpha-3 filter (e.g. NGA)
    latest_only: bool = True  # Exclude superseded signal versions


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
