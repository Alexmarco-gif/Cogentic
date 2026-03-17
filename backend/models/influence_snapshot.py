"""Influence snapshot model — periodic measurements of entity influence metrics.

Stores point-in-time influence scores for entities so the system can track
how influence changes over time (rising stars, declining powers, stability).
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, UUIDMixin


class InfluenceSnapshot(Base, UUIDMixin):
    """Point-in-time influence measurement for an entity."""

    __tablename__ = "influence_snapshots"

    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # When this snapshot was taken
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Composite influence score
    influence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Individual centrality metrics
    pagerank: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    betweenness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    eigenvector: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    degree: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    closeness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Network context at time of snapshot
    network_size: Mapped[int | None] = mapped_column(nullable=True)
    direct_connections: Mapped[int | None] = mapped_column(nullable=True)

    # Optional industry scope
    industry_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Extra data (algorithm params, notes, etc.)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Descriptive label (e.g. the algorithm or trigger)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<InfluenceSnapshot entity={self.entity_id} "
            f"date={self.snapshot_date} score={self.influence_score:.4f}>"
        )
