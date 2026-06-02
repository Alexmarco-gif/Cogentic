"""ML Pipeline API endpoints.

Provides endpoints for:
  - Viewing signal scores
  - ML model status and registry
  - Manual training triggers
  - Manual refinement triggers
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user, require_permissions
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.repositories.ml_model_registry import MLModelRegistryRepository
from backend.repositories.ml_model_run import MLModelRunRepository
from backend.repositories.signal_score import SignalScoreRepository
from backend.schemas.ml import (
    MLModelRegistryResponse,
    MLModelRunResponse,
    MLStatusResponse,
    RefinementResponse,
    SignalScoreResponse,
    SignalScoresResponse,
    TrainAllQueuedResponse,
    TrainingRequest,
    TrainingResponse,
)

router = APIRouter(prefix="/ml")


# ── Signal Scores ────────────────────────────────────────────────────


@router.get(
    "/signals/{signal_id}/scores",
    response_model=SignalScoresResponse,
)
async def get_signal_scores(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get all ML scores for a specific signal."""
    repo = SignalScoreRepository(db)
    scores = await repo.get_by_signal(signal_id)
    return SignalScoresResponse(
        signal_id=signal_id,
        scores=[SignalScoreResponse.model_validate(s) for s in scores],
    )


# ── ML Status ────────────────────────────────────────────────────────


@router.get(
    "/status",
    response_model=MLStatusResponse,
)
async def get_ml_status(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get overall ML pipeline status: available models, latest runs, registry."""
    try:
        from backend.ml.inference import get_inference_engine
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="ML inference dependencies are not installed in this deployment.",
        ) from exc

    engine = get_inference_engine()
    run_repo = MLModelRunRepository(db)
    registry_repo = MLModelRegistryRepository(db)

    # Available models in ONNX engine
    model_names = ["anomaly_detector", "trending_scorer", "confidence_calibrator"]
    available = [m for m in model_names if engine.is_model_available(m)]

    # Latest runs per model
    latest_runs = []
    for name in model_names:
        run = await run_repo.get_latest_run(name)
        if run:
            latest_runs.append(MLModelRunResponse.model_validate(run))

    # Registered models
    registered = []
    for name in model_names:
        entry = await registry_repo.get_active_version(name)
        if entry:
            registered.append(MLModelRegistryResponse.model_validate(entry))

    return MLStatusResponse(
        models_available=available,
        latest_runs=latest_runs,
        registered_models=registered,
    )


# ── Model Runs ───────────────────────────────────────────────────────


@router.get(
    "/runs",
    response_model=list[MLModelRunResponse],
)
async def get_model_runs(
    model_name: str | None = None,
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(20, ge=1, le=200, description="Max records to return"),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get recent ML model runs (optionally filtered by model name)."""
    repo = MLModelRunRepository(db)
    if model_name:
        runs = await repo.get_by_model(model_name, skip=skip, limit=limit)
    else:
        runs = await repo.get_multi(skip=skip, limit=limit)
    return [MLModelRunResponse.model_validate(r) for r in runs]


# ── Model Registry ───────────────────────────────────────────────────


@router.get(
    "/registry",
    response_model=list[MLModelRegistryResponse],
)
async def get_model_registry(
    model_name: str | None = None,
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get registered model versions."""
    repo = MLModelRegistryRepository(db)
    if model_name:
        entries = await repo.get_versions(model_name, limit=limit)
    else:
        entries = await repo.get_multi(skip=skip, limit=limit)
    return [MLModelRegistryResponse.model_validate(e) for e in entries]


# ── Training ─────────────────────────────────────────────────────────


@router.post(
    "/train",
    response_model=TrainingResponse,
)
async def train_model(
    request: TrainingRequest,
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Trigger training of a specific ML model (async via RQ).

    Only admins can trigger training.
    """

    from backend.job_queue import enqueue_job
    from backend.jobs.refinement_job import train_single_model

    job = enqueue_job(
        train_single_model,
        request.model_name,
        queue_name="low",
        job_timeout="30m",
    )
    return TrainingResponse(
        status="queued",
        model_name=request.model_name,
        job_id=job.id,
        path=None,
    )


@router.post(
    "/train/all",
    response_model=TrainAllQueuedResponse,
)
async def train_all_models(
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Trigger training of all 3 ML models (async via RQ)."""

    from backend.job_queue import enqueue_job
    from backend.jobs.refinement_job import train_all_models

    job = enqueue_job(
        train_all_models,
        queue_name="low",
        job_timeout="30m",
    )
    return TrainAllQueuedResponse(status="queued", jobs=[job.id])


# ── Refinement ───────────────────────────────────────────────────────


@router.post(
    "/refine/unprocessed",
    response_model=RefinementResponse,
)
async def refine_unprocessed(
    limit: int = 100,
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Trigger refinement of unprocessed signals (async via RQ)."""

    from backend.job_queue import enqueue_job
    from backend.jobs.refinement_job import refine_unprocessed

    enqueue_job(
        refine_unprocessed,
        limit,
        queue_name="default",
        job_timeout="30m",
    )
    return RefinementResponse()
