"""Discovered Source model — URLs/sources found in signal content.

When signals reference external URLs or data sources that the system
doesn't currently track via SignalContract, those references are captured
here. High-frequency or high-relevance discoveries can be promoted to
active signal contracts — either automatically or via human review.

This is part of the "living contracts" upgrade that makes the system's
aperture grow dynamically instead of being fixed to seeded contracts.
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.signal import Signal
    from backend.models.signal_contract import SignalContract


class DiscoveredSource(Base, UUIDMixin, TimestampMixin):
    """A URL or data source discovered from signal content.

    Lifecycle:
      1. discovered — first seen in a signal, tracked for frequency
      2. recommended — mention_count or relevance passes threshold, suggested for activation
      3. activated — promoted to a real SignalContract (activated_contract_id set)
      4. dismissed — human/system decided not to track this source

    The source_discovery service manages the lifecycle.
    """

    __tablename__ = "discovered_sources"
    __table_args__ = (
        UniqueConstraint("url_hash", name="uq_discovered_sources_url_hash"),
    )

    # Source identity
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 of normalized URL for dedup",
    )
    domain: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Extracted domain (e.g., cbn.gov.ng)",
    )
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Inferred source name (e.g., 'Central Bank of Nigeria')",
    )

    # Classification
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
        server_default="unknown",
        comment="Inferred: api | scraper | rss | social | government | research | news",
    )
    signal_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Inferred signal type: regulatory, market, financial, news, etc.",
    )

    # Discovery tracking
    first_seen_signal_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
        comment="Signal where this source was first discovered",
    )
    mention_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Number of signals that reference this source",
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relevance scoring
    relevance_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        server_default="0.5",
        comment="Computed relevance (0-1) based on mention frequency + signal quality",
    )

    # Lifecycle status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="discovered",
        server_default="discovered",
        index=True,
        comment="discovered | recommended | activated | dismissed",
    )

    # Activation link
    activated_contract_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("signal_contracts.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to the SignalContract created when this source was activated",
    )

    # Metadata
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
        comment="Extra metadata: inferred schedule, content samples, etc.",
    )

    # Relationships
    first_seen_signal: Mapped["Signal | None"] = relationship(
        foreign_keys=[first_seen_signal_id]
    )
    activated_contract: Mapped["SignalContract | None"] = relationship(
        foreign_keys=[activated_contract_id]
    )

    def __repr__(self) -> str:
        return f"<DiscoveredSource {self.domain} status={self.status} mentions={self.mention_count}>"
