"""Signal Contract model — defines HOW to acquire a signal"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.entity import Entity
    from backend.models.industry import Industry
    from backend.models.signal import Signal


class SignalContract(Base, UUIDMixin, TimestampMixin):
    """Defines how to acquire a signal from a specific source.

    280 contracts seeded across 4 industries (70 per industry).
    Each contract specifies source URL, extraction rules, refresh schedule,
    and entity mapping.
    """

    __tablename__ = "signal_contracts"

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Industry & entity mapping
    industry_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Source configuration
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # api, scraper, rss, social

    # Scheduling
    refresh_cron: Mapped[str] = mapped_column(
        String(100), nullable=False, default="0 */1 * * *"
    )  # Default: hourly
    schedule_tier: Mapped[str] = mapped_column(
        String(50), nullable=False, default="standard"
    )  # realtime (15min), standard (1hr), slow (6hr), daily

    # Extraction configuration
    extraction_config: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default="{}"
    )  # CSS selectors, JSON paths, API params

    # Status & health
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="active", index=True
    )  # active, degraded, disabled
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    max_failures: Mapped[int] = mapped_column(Integer, default=3)
    last_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    industry: Mapped["Industry"] = relationship(
        back_populates="signal_contracts",
    )
    entity: Mapped["Entity | None"] = relationship()
    signals: Mapped[list["Signal"]] = relationship(
        back_populates="contract",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SignalContract {self.name} source={self.source_type} status={self.status}>"
