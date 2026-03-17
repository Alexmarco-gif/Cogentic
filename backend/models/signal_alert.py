"""Signal Alert model — anomaly, threshold, and trend-break alerts."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.entity import Entity
    from backend.models.signal import Signal


class SignalAlert(Base, UUIDMixin, TimestampMixin):
    """An alert generated when a market metric or signal score crosses a threshold.

    Alert types:
      - anomaly: z-score deviation > 2.0 from rolling 30-day basline
      - threshold: absolute value above/below a configured limit
      - trend_break: velocity reversal detected on a metric

    Severity levels: low, medium, high, critical
    """

    __tablename__ = "signal_alerts"

    # Source
    signal_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Alert identity
    alert_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # anomaly | threshold | trend_break
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium", index=True
    )  # low | medium | high | critical
    metric: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    country_code: Mapped[str | None] = mapped_column(
        String(10), nullable=True, index=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Values
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    deviation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Acknowledgement
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    signal: Mapped["Signal | None"] = relationship()
    entity: Mapped["Entity | None"] = relationship()

    def __repr__(self) -> str:
        return f"<SignalAlert {self.alert_type}/{self.severity} metric={self.metric}>"
