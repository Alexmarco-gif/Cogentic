"""Signal Pipeline API — scheduler control and pipeline status.

Admin endpoints for managing the signal acquisition pipeline.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.guards import require_role
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.queue import enqueue_job, get_queue_stats
from backend.repositories.signal_contract import SignalContractRepository
from backend.schemas.signals import FetchTierRequest, PipelineStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline")


@router.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get signal acquisition pipeline status."""
    from backend.signals.scheduler import get_scheduler

    scheduler = get_scheduler()
    repo = SignalContractRepository(db)

    active = await repo.get_active_contracts()
    degraded = await repo.get_degraded_contracts()

    return PipelineStatusResponse(
        scheduler_running=scheduler.is_running,
        active_contracts=len(active),
        degraded_contracts=len(degraded),
        degraded_names=[c.name for c in degraded],
    )


@router.post("/fetch")
async def trigger_tier_fetch(
    body: FetchTierRequest,
    auth: AuthContext = Depends(get_current_user),
):
    """Manually trigger a fetch for all contracts in a tier.

    Enqueues an RQ job — does not block. Requires admin role.
    """
    require_role(auth, "admin")
    from backend.jobs.acquisition_job import fetch_signals_by_tier

    queue_name = "high" if body.tier == "realtime" else "default"
    job = enqueue_job(
        fetch_signals_by_tier,
        body.tier,
        queue_name=queue_name,
        job_timeout="15m",
    )
    return {
        "status": "queued",
        "job_id": job.id,
        "tier": body.tier,
    }


@router.get("/queues")
async def get_pipeline_queues(
    auth: AuthContext = Depends(get_current_user),
):
    """Get RQ queue statistics."""
    return get_queue_stats()


@router.post("/scheduler/start")
async def start_scheduler(
    auth: AuthContext = Depends(get_current_user),
):
    """Start the signal acquisition scheduler. Requires admin role."""
    require_role(auth, "admin")
    from backend.signals.scheduler import get_scheduler

    scheduler = get_scheduler()
    if scheduler.is_running:
        return {"status": "already_running"}

    scheduler.start()
    return {"status": "started"}


@router.post("/scheduler/stop")
async def stop_scheduler(
    auth: AuthContext = Depends(get_current_user),
):
    """Stop the signal acquisition scheduler. Requires admin role."""
    require_role(auth, "admin")
    from backend.signals.scheduler import get_scheduler

    scheduler = get_scheduler()
    if not scheduler.is_running:
        return {"status": "not_running"}

    scheduler.stop()
    return {"status": "stopped"}
