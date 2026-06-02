"""Pydantic schemas for ML pipeline operations.

Request/response models for ML scoring, training, and model registry endpoints.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ── Signal Score Schemas ─────────────────────────────────────────────


class SignalScoreResponse(BaseModel):
    """Individual ML score for a signal."""

    id: UUID
    signal_id: UUID
    score_type: str
    score_value: float
    model_run_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SignalScoresResponse(BaseModel):
    """All scores for a signal."""

    signal_id: UUID
    scores: list[SignalScoreResponse]


# ── ML Model Run Schemas ─────────────────────────────────────────────


class MLModelRunResponse(BaseModel):
    """ML pipeline run audit record."""

    id: UUID
    model_name: str
    model_version: str
    signals_processed: int
    duration_ms: int | None
    status: str
    error_message: str | None
    ran_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Model Registry Schemas ───────────────────────────────────────────


class MLModelRegistryResponse(BaseModel):
    """Registered model version."""

    id: UUID
    model_name: str
    model_version: str
    description: str | None
    artifact_path: str
    artifact_size_bytes: int | None
    metrics: dict[str, Any]
    status: str
    training_samples: int | None
    training_duration_ms: int | None
    trained_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Training Schemas ─────────────────────────────────────────────────


class TrainingRequest(BaseModel):
    """Request to train a specific model."""

    model_name: str = Field(
        ...,
        pattern=r"^(anomaly_detector|trending_scorer|confidence_calibrator)$",
    )


class TrainingResponse(BaseModel):
    """Training job result."""

    status: str
    model_name: str | None = None
    job_id: str | None = None
    path: str | None = None
    error: str | None = None


class TrainAllQueuedResponse(BaseModel):
    """Queued training jobs for the model set."""

    status: str
    jobs: list[str]


class TrainAllResponse(BaseModel):
    """Result of training all models."""

    models: dict[str, TrainingResponse]
    duration_seconds: float


# ── Refinement Schemas ───────────────────────────────────────────────


class RefinementRequest(BaseModel):
    """Request to refine signals."""

    signal_ids: list[UUID] = Field(default_factory=list, max_length=500)
    limit: int = Field(default=100, ge=1, le=1000)


class RefinementResponse(BaseModel):
    """Refinement job result."""

    total: int = 0
    refined: int = 0
    duplicates: int = 0
    errors: int = 0
    duration_ms: int = 0


# ── ML Status Schema ─────────────────────────────────────────────────


class MLStatusResponse(BaseModel):
    """Overall ML pipeline status."""

    models_available: list[str]
    latest_runs: list[MLModelRunResponse]
    registered_models: list[MLModelRegistryResponse]
