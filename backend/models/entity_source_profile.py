"""Entity source profile — cross-source data fusion layer.

Stores external data profiles from multiple sources (CAC filings, customs,
LinkedIn, job boards, procurement tenders, etc.) for a single canonical entity.
Each entity can have one profile per source type.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.entity import Entity


class EntitySourceProfile(Base, UUIDMixin, TimestampMixin):
    """Cross-source entity profile for data fusion.

    source_type values:
      - cac_nigeria: Corporate Affairs Commission filings
      - customs_data: Import/export manifests
      - linkedin: LinkedIn company/person data
      - job_boards: Job postings (Jobberman, LinkedIn Jobs)
      - procurement: Government/private tender documents
      - financial_filings: SEC Nigeria, annual reports
      - social_media: Twitter/X, Nairaland presence
      - news_mentions: Aggregated news coverage metrics
      - web_presence: Website metadata, traffic estimates

    profile_data: JSONB blob storing source-specific structured data.
    """

    __tablename__ = "entity_source_profiles"
    __table_args__ = (
        UniqueConstraint(
            "entity_id",
            "source_type",
            name="uq_entity_source_profile",
        ),
    )

    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)

    # Relationships
    entity: Mapped["Entity"] = relationship(
        back_populates="source_profiles",
    )

    def __repr__(self) -> str:
        return (
            f"<EntitySourceProfile entity={self.entity_id} source={self.source_type}>"
        )
