"""Intelligence Brief model"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.brief_signal import BriefSignal
    from backend.models.industry import Industry
    from backend.models.organization import Organization


class IntelligenceBrief(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Pre-built and auto-generated intelligence briefs.

    20 pre-built briefs (5 per industry) seeded for Day-1.
    Structure: Checklist → BLUF → Evidence → Outlook → Decision Lens.

    org_id=NULL means global/template brief (visible to all orgs).
    org_id set means org-specific customized brief.
    """

    __tablename__ = "intelligence_briefs"

    # Scoping
    org_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,  # NULL = global/template brief
        index=True,
    )
    industry_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    brief_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pre_built"
    )  # pre_built, auto_generated
    bluf: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Bottom Line Up Front (2 sentences max)
    body_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default="{}"
    )  # Structured: argument, evidence, checklist
    outlook: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_lens: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # "What this means for you" panel

    # Status & freshness
    status: Mapped[str] = mapped_column(
        String(50), default="draft", index=True
    )  # draft, published, archived
    refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organization: Mapped["Organization | None"] = relationship()
    industry: Mapped["Industry"] = relationship(back_populates="briefs")
    signal_links: Mapped[list["BriefSignal"]] = relationship(
        back_populates="brief",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<IntelligenceBrief {self.title} status={self.status}>"
