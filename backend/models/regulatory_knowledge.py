"""Regulatory knowledge models for dynamic contextual intelligence.

Schema aligned with alembic migration 2026_02_14_0001.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class RegulatoryEvent(Base):
    """Tracks regulatory changes, policy announcements, and government actions."""

    __tablename__ = "regulatory_events"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    issuing_body: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    announced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    effective_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    effective_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deadline_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    severity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_complexity: Mapped[str | None] = mapped_column(String(20), nullable=True)

    affected_sectors: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    affected_entity_types: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )

    requirements: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    exemptions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    penalties: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_document_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_signal_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    source_event_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("regulatory_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    historical_precedents: Mapped[list[UUID] | None] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=True,
    )
    content_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536), nullable=True
    )

    verified_by_expert: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    rules: Mapped[list["RegulatoryRule"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    impacts: Mapped[list["RegulatoryImpact"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )


class RegulatoryRule(Base):
    """Dynamic business rules extracted from regulatory events."""

    __tablename__ = "regulatory_rules"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    event_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("regulatory_events.id", ondelete="CASCADE"),
        nullable=False,
    )

    rule_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    condition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    action: Mapped[dict] = mapped_column(JSONB, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    effective_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    effective_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    application_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    interpretation_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    event: Mapped[RegulatoryEvent] = relationship(back_populates="rules")


class RegulatoryImpact(Base):
    """Tracks observed impacts of regulatory events on entities/markets."""

    __tablename__ = "regulatory_impacts"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    event_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("regulatory_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    impact_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    post_impact_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    percentage_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    lag_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observation_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    supporting_signal_ids: Mapped[list[UUID] | None] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=True,
    )
    evidence_quality: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confounding_factors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    recorded_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    event: Mapped[RegulatoryEvent] = relationship(back_populates="impacts")


class RegulatoryPattern(Base):
    """Learned patterns about regulatory behavior and impact sequences."""

    __tablename__ = "regulatory_patterns"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    pattern_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    trigger_conditions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sequence: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    typical_impacts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    frequency_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prediction_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_interval_lower: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    confidence_interval_upper: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    first_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
