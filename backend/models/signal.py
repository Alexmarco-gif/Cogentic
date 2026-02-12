"""Signal model — raw acquired signal instances"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.organization import Organization
    from backend.models.signal_contract import SignalContract
    from backend.models.signal_entity import SignalEntity
    from backend.models.signal_score import SignalScore


class Signal(Base, UUIDMixin, TimestampMixin):
    """Raw acquired signal instance from a signal contract.

    Global signals (org_id=NULL) are visible to all orgs.
    Org-specific signals can be created for custom needs.

    Confidence scoring:
      - >= 0.85: brief-eligible
      - >= 0.60: visible in catalog
      - < 0.60: flagged, excluded from briefs
    """

    __tablename__ = "signals"

    # Source reference
    contract_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("signal_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Multi-tenancy (nullable = global signal)
    org_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Content
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_data: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default="{}"
    )
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Classification
    signal_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # news, social, regulatory, financial, market, technology

    # Quality & scoring
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5
    )  # 0.0 to 1.0

    # Deduplication (SHA-256 of content)
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )

    # Timing
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )  # 90-day retention

    # pgvector embedding (text-embedding-3-small, 1536 dimensions)
    embedding: Mapped[Any | None] = mapped_column(Vector(1536), nullable=True)

    # Relationships
    contract: Mapped["SignalContract"] = relationship(
        back_populates="signals",
    )
    organization: Mapped["Organization | None"] = relationship()
    entity_links: Mapped[list["SignalEntity"]] = relationship(
        back_populates="signal",
        cascade="all, delete-orphan",
    )
    scores: Mapped[list["SignalScore"]] = relationship(
        back_populates="signal",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Signal {self.title or self.id} conf={self.confidence}>"
