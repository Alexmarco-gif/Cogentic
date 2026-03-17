"""Market data point model — time-series price/rate tracking extracted from signals.

Stores structured numeric data extracted by NER for trend analysis:
  - Commodity prices (rice ₦/bag, crude oil $/barrel, cocoa GHS/tonne)
  - Forex rates (NGN/USD parallel, EGP/USD, KES/USD)
  - Interest rates, inflation figures, index values
  - Volume data (trade volumes, production tonnage)

Each data point is linked to the signal it was extracted from, the entity it
relates to (optional), and carries ISO-4217 currency + metric metadata so the
frontend can chart and compare across sources.

This is part of the Phase 3 intelligence upgrade — enables "was ₦X, now ₦Y"
reasoning instead of just raw signal text.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.entity import Entity
    from backend.models.signal import Signal


class MarketDataPoint(Base, UUIDMixin, TimestampMixin):
    """A single time-series data point extracted from a signal.

    Examples:
      - metric="rice_price", value=82000, unit="NGN/50kg", currency="NGN"
      - metric="parallel_exchange_rate", value=1580, unit="NGN/USD", currency="NGN"
      - metric="inflation_rate", value=29.9, unit="percent", currency=None
      - metric="crude_oil_price", value=78.5, unit="USD/barrel", currency="USD"
    """

    __tablename__ = "market_data_points"
    __table_args__ = (
        Index(
            "ix_market_data_metric_observed",
            "metric",
            "observed_at",
            postgresql_using="btree",
        ),
        Index(
            "ix_market_data_entity",
            "entity_id",
            "metric",
            "observed_at",
            postgresql_using="btree",
        ),
    )

    # ── Core value ─────────────────────────────────────────────────────

    metric: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
        comment="Normalized metric name (e.g. rice_price, ngn_usd_parallel, inflation_rate)",
    )
    value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Numeric value of the data point",
    )
    unit: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Unit of measurement (NGN/50kg, USD/barrel, percent, index)",
    )
    currency: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
        comment="ISO 4217 currency code if applicable (NGN, USD, KES, etc.)",
    )

    # ── Temporal ───────────────────────────────────────────────────────

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When this data point was observed/published (not when we extracted it)",
    )

    # ── Source linkage ─────────────────────────────────────────────────

    signal_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Signal this data point was extracted from",
    )

    entity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Entity this data point relates to (e.g. 'BUA Cement' for cement price)",
    )

    # ── Geography ──────────────────────────────────────────────────────

    country_code: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
        index=True,
        comment="ISO 3166-1 alpha-3 country code (NGA, KEN, etc.)",
    )
    region: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="State/region/market location (e.g. Lagos, Mile 12)",
    )

    # ── Context ────────────────────────────────────────────────────────

    context: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Brief surrounding text explaining the data point",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.8,
        server_default="0.8",
        comment="Extraction confidence (0-1)",
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=None,
        comment="Additional structured metadata",
    )

    # ── Relationships ──────────────────────────────────────────────────

    signal: Mapped["Signal | None"] = relationship(
        "Signal",
        foreign_keys=[signal_id],
        lazy="selectin",
    )
    entity: Mapped["Entity | None"] = relationship(
        "Entity",
        foreign_keys=[entity_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<MarketDataPoint metric={self.metric!r} value={self.value} "
            f"unit={self.unit!r} at={self.observed_at}>"
        )
