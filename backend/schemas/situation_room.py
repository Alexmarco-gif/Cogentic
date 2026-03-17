"""Pydantic schemas for Situation Room.

Request/response models for the live industry dashboard (REST snapshot)
and WebSocket real-time signal feed.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────


class SituationRoomEventType(str, Enum):
    """WebSocket message types pushed to clients."""

    INITIAL_STATE = "initial_state"
    NEW_SIGNAL = "new_signal"
    SIGNAL_UPDATED = "signal_updated"
    BRIEF_PUBLISHED = "brief_published"
    ANOMALY_DETECTED = "anomaly_detected"
    METRICS_UPDATE = "metrics_update"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class SignalPriority(str, Enum):
    """Signal priority levels derived from confidence + anomaly scores."""

    CRITICAL = "critical"  # anomaly + confidence >= 0.85
    HIGH = "high"  # confidence >= 0.85
    MEDIUM = "medium"  # confidence >= 0.60
    LOW = "low"  # confidence < 0.60


# ── Signal Feed Item ─────────────────────────────────────────────────


class SignalFeedItem(BaseModel):
    """A single signal in the live feed."""

    id: UUID
    title: str | None
    summary: str | None
    signal_type: str
    source_url: str | None
    confidence: float
    priority: SignalPriority
    published_at: datetime | None
    fetched_at: datetime
    is_anomaly: bool = False
    anomaly_score: float | None = None
    trending_score: float | None = None
    entity_names: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ── Dashboard Metrics ────────────────────────────────────────────────


class SignalTypeBreakdown(BaseModel):
    """Count of signals by type."""

    signal_type: str
    count: int
    percentage: float


class TrendPoint(BaseModel):
    """A single data point in a time series trend."""

    timestamp: datetime
    value: float


class DashboardMetrics(BaseModel):
    """Aggregate metrics for the industry dashboard."""

    total_signals: int
    signals_last_24h: int
    signals_last_7d: int
    avg_confidence: float
    anomaly_count: int
    high_priority_count: int
    active_briefs: int
    type_breakdown: list[SignalTypeBreakdown] = Field(default_factory=list)
    signal_volume_trend: list[TrendPoint] = Field(
        default_factory=list,
        description="Daily signal volume for the past 14 days",
    )
    confidence_trend: list[TrendPoint] = Field(
        default_factory=list,
        description="Daily average confidence for the past 14 days",
    )


# ── Active Alert ─────────────────────────────────────────────────────


class ActiveAlert(BaseModel):
    """High-priority signal or anomaly requiring attention."""

    signal_id: UUID
    title: str | None
    signal_type: str
    confidence: float
    anomaly_score: float | None
    reason: str
    detected_at: datetime


# ── Brief Summary ────────────────────────────────────────────────────


class BriefSummary(BaseModel):
    """Condensed brief for the situation room sidebar."""

    id: UUID
    title: str
    bluf: str | None
    status: str
    refreshed_at: datetime | None
    signal_count: int = 0


# ── Dashboard Snapshot (REST response) ───────────────────────────────


class SituationRoomDashboard(BaseModel):
    """Full snapshot returned by GET /api/v1/situation-room/{industry}."""

    industry_id: UUID
    industry_name: str
    industry_slug: str
    metrics: DashboardMetrics
    recent_signals: list[SignalFeedItem] = Field(
        default_factory=list,
        description="Latest 50 signals for the industry",
    )
    active_alerts: list[ActiveAlert] = Field(
        default_factory=list,
        description="Anomalies and high-priority signals",
    )
    published_briefs: list[BriefSummary] = Field(
        default_factory=list,
        description="Published briefs for this industry",
    )
    generated_at: datetime


# ── WebSocket Messages ───────────────────────────────────────────────


class WSMessage(BaseModel):
    """Envelope for all WebSocket messages (server → client)."""

    event: SituationRoomEventType
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    industry_id: UUID | None = None


class WSSubscribeRequest(BaseModel):
    """Client → server: subscribe to an industry room."""

    action: str = "subscribe"  # subscribe | unsubscribe
    industry_id: UUID


# ── Query Parameters ─────────────────────────────────────────────────


class SituationRoomQuery(BaseModel):
    """Query parameters for the REST dashboard endpoint."""

    signal_types: list[str] | None = Field(
        default=None,
        description="Filter by signal type(s): news, social, regulatory, financial, market, technology",
    )
    min_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold",
    )
    hours: int = Field(
        default=168,
        ge=1,
        le=720,
        description="Lookback window in hours (default 7 days, max 30 days)",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Max signals in feed",
    )
