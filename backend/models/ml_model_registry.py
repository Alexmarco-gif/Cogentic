"""ML Model Registry — tracks model versions, metrics, artifact paths"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDMixin


class MLModelRegistry(Base, UUIDMixin, TimestampMixin):
    """Registry entry for a trained ML model version.

    Tracks:
      - Model identity (name, version)
      - Artifact location (local path or Azure Blob URI)
      - Training metrics (accuracy, R², etc.)
      - Status lifecycle (training → active → archived)
    """

    __tablename__ = "ml_model_registry"

    # Model identity
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # anomaly_detector, trending_scorer, confidence_calibrator
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Artifact
    artifact_path: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # local path or blob URI
    artifact_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Training metrics (JSON: {"accuracy": 0.95, "r2": 0.87, ...})
    metrics: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="active", index=True
    )  # training, active, archived

    # Training metadata
    training_samples: Mapped[int | None] = mapped_column(Integer, nullable=True)
    training_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<MLModelRegistry {self.model_name} v{self.model_version} "
            f"status={self.status}>"
        )
