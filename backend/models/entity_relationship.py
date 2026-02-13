"""Entity relationship model — directed graph of entity connections.


Tracks relationships between entities (supplier, customer, competitor,
subsidiary, partner, regulator, etc.) with strength scoring, confidence,
and evidence lineage back to supporting signals.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.entity import Entity


class EntityRelationship(Base, UUIDMixin, TimestampMixin):
    """Directed relationship between two entities.

    relationship_type values:
      - subsidiary: Source owns/controls target
      - parent: Target owns/controls source (inverse of subsidiary)
      - supplier: Target supplies to source
      - customer: Target buys from source
      - competitor: Source competes with target
      - partner: Strategic/commercial partnership
      - investor: Source invests in target
      - regulator: Source regulates target
      - executive_link: Shared executive/board member
      - supply_chain: General supply chain connection

    Strength (0..1): How strong/important this relationship is.
    Confidence (0..1): How confident we are that this relationship exists.
    Evidence: Array of signal IDs that support this relationship.
    """

    __tablename__ = "entity_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            name="uq_entity_relationship",
        ),
    )

    source_entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    # Scoring
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    bidirectional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Evidence lineage (signal IDs that support this relationship)
    evidence_signals: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )

    # Temporal tracking
    first_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    source_entity: Mapped["Entity"] = relationship(
        foreign_keys=[source_entity_id],
        back_populates="outgoing_relationships",
    )
    target_entity: Mapped["Entity"] = relationship(
        foreign_keys=[target_entity_id],
        back_populates="incoming_relationships",
    )

    def __repr__(self) -> str:
        return (
            f"<EntityRelationship {self.relationship_type} "
            f"from={self.source_entity_id} to={self.target_entity_id} "
            f"strength={self.strength}>"
        )
