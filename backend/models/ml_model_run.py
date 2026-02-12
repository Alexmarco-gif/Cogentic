"""ML Model Run model — pipeline audit trail"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDMixin


class MLModelRun(Base, UUIDMixin, TimestampMixin):
    """ML pipeline execution audit trail.

    Day-1 models (3):
      - anomaly_detector (Isolation Forest)
      - trending_scorer (time-series slope)
      - confidence_calibrator (logistic regression)

    All trained on seeded data, weekly retrain via cron.
    Inference via ONNX Runtime.
    """

    __tablename__ = "ml_model_runs"

    # Model identity
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # anomaly_detector, trending_scorer, confidence_calibrator
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Execution
    input_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # SHA-256 of input data
    output_json: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    signals_processed: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="completed", index=True
    )  # running, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    ran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<MLModelRun {self.model_name} v{self.model_version} status={self.status}>"
        )
