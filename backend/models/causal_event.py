"""Causal event model — temporal event nodes for causal reasoning.

Stores events extracted from signals with typed classification,
enabling causal chain detection and predictive analysis.
Events form the nodes of the causal reasoning graph; causal edges
record discovered cause-effect relationships between events.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.signal import Signal


class CausalEvent(Base, UUIDMixin, TimestampMixin):
    """An event extracted from a signal for causal reasoning.

    event_category values:
      - policy: Government/regulatory policy change
      - market: Market price, volume, or demand change
      - corporate: Company-level action (earnings, launch, M&A)
      - infrastructure: Physical infrastructure change (port, road, power)
      - social: Social/cultural event or trend shift
      - environmental: Weather, natural disaster, climate event
      - financial: Monetary policy, FX, interest rate change
      - technology: Tech adoption, disruption event

    Each event links back to the signal it was extracted from and
    stores which entities are involved.
    """

    __tablename__ = "causal_events"

    # Source signal reference
    signal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Event classification
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Temporal
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Entity references (array of entity UUIDs involved)
    entity_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )

    # Structured attributes for domain-specific data
    attributes: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Quality
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)

    # Relationships
    signal: Mapped["Signal"] = relationship()
    caused_edges: Mapped[list["CausalEdge"]] = relationship(
        foreign_keys="CausalEdge.cause_event_id",
        back_populates="cause_event",
        cascade="all, delete-orphan",
    )
    effect_edges: Mapped[list["CausalEdge"]] = relationship(
        foreign_keys="CausalEdge.effect_event_id",
        back_populates="effect_event",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<CausalEvent {self.event_type} at {self.event_timestamp} "
            f"conf={self.confidence}>"
        )


class CausalEdge(Base, UUIDMixin, TimestampMixin):
    """A discovered causal edge between two events.

    Represents: cause_event --[LEADS_TO]--> effect_event
    with measured/estimated lag, confidence, and supporting evidence.

    These edges form the core of the temporal causal graph and are used
    for predictive analysis and counterfactual reasoning.
    """

    __tablename__ = "causal_edges"
    __table_args__ = (
        UniqueConstraint(
            "cause_event_id",
            "effect_event_id",
            "relationship_label",
            name="uq_causal_edges_cause_effect_label",
        ),
    )

    cause_event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("causal_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    effect_event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("causal_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationship classification
    relationship_label: Mapped[str] = mapped_column(
        String(100), nullable=False, default="leads_to"
    )

    # Causal metrics
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    lag_days_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lag_days_max: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lag_days_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Evidence strength
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Statistical metadata
    p_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    correlation: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Discovery metadata
    discovery_method: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual"
    )  # manual, granger_test, pattern_mining, llm_extraction

    # Relationships
    cause_event: Mapped["CausalEvent"] = relationship(
        foreign_keys=[cause_event_id],
        back_populates="caused_edges",
    )
    effect_event: Mapped["CausalEvent"] = relationship(
        foreign_keys=[effect_event_id],
        back_populates="effect_edges",
    )

    def __repr__(self) -> str:
        return (
            f"<CausalEdge {self.cause_event_id} → {self.effect_event_id} "
            f"lag={self.lag_days_avg}d conf={self.confidence}>"
        )
