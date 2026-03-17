"""Signal Score model — ML-computed scores per signal"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.ml_model_run import MLModelRun
    from backend.models.signal import Signal


class SignalScore(Base, UUIDMixin, TimestampMixin):
    """ML-computed scores for a signal.

    Score types:
      - anomaly: Isolation Forest anomaly score
      - trending: time-series slope score
      - confidence: calibrated confidence score
    """

    __tablename__ = "signal_scores"
    __table_args__ = (
        UniqueConstraint("signal_id", "score_type", name="uq_signal_scores_signal_type"),
    )

    signal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # anomaly, trending, confidence
    score_value: Mapped[float] = mapped_column(Float, nullable=False)
    model_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ml_model_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    signal: Mapped["Signal"] = relationship(back_populates="scores")
    model_run: Mapped["MLModelRun | None"] = relationship()

    def __repr__(self) -> str:
        return f"<SignalScore signal={self.signal_id} type={self.score_type} value={self.score_value}>"
