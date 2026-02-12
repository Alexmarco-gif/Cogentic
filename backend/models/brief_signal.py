"""Brief-Signal many-to-many join table"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.intelligence_brief import IntelligenceBrief
    from backend.models.signal import Signal


class BriefSignal(Base, UUIDMixin, TimestampMixin):
    """Many-to-many relationship between briefs and signals with relevance ranking.

    ~14 signals per brief (70 signals ÷ 5 briefs per industry).
    """

    __tablename__ = "brief_signals"
    __table_args__ = (
        UniqueConstraint("brief_id", "signal_id", name="uq_brief_signal"),
    )

    brief_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("intelligence_briefs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relevance_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    brief: Mapped["IntelligenceBrief"] = relationship(back_populates="signal_links")
    signal: Mapped["Signal"] = relationship()

    def __repr__(self) -> str:
        return f"<BriefSignal brief={self.brief_id} signal={self.signal_id} rank={self.relevance_rank}>"
