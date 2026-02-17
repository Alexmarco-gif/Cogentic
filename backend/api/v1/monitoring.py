"""System Monitoring & Metrics API.

Provides visibility into SLOs, cache performance, circuit breakers, and cost usage.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user, require_permissions
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.jobs.retry_strategy import DeadLetterQueue
from backend.services.cache_metrics import CacheMetrics
from backend.services.circuit_breaker import openai_breaker
from backend.services.cost_tracker import CostTracker
from backend.services.slo_metrics import SLOMetrics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring")


@router.get("/slo")
async def get_slo_metrics(
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Get SLO compliance metrics for all operations. Requires admin or owner role."""
    return {
        "metrics": await SLOMetrics.get_all_stats(),
    }


@router.get("/cache")
async def get_cache_metrics(
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Get cache hit rate metrics. Requires admin or owner role."""
    return {
        "metrics": await CacheMetrics.get_all_stats(),
        "target_hit_rate": 70.0,
    }


@router.get("/circuit-breakers")
async def get_circuit_breaker_status(
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Get circuit breaker status. Requires admin or owner role."""
    return {
        "openai": await openai_breaker.get_status(),
    }


@router.get("/cost/budget")
async def get_cost_budget(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Get AI usage budget status for current user/org. Requires admin or owner role."""
    tracker = CostTracker(db)
    return await tracker.check_budget(auth.user_id, auth.org_id)


@router.get("/cost/summary")
async def get_cost_summary(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Get AI usage cost summary for last N days. Requires admin or owner role."""
    tracker = CostTracker(db)
    return await tracker.get_usage_summary(auth.org_id, days=days)


@router.get("/dlq")
async def get_dead_letter_queue(
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Get jobs in dead letter queue. Requires admin or owner role."""
    return {
        "jobs": DeadLetterQueue.get_all(),
    }


@router.get("/health")
async def get_system_health(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Get overall system health summary. Requires admin or owner role."""
    # SLO compliance
    slo_stats = await SLOMetrics.get_all_stats()
    meeting_slos = sum(1 for s in slo_stats if s["meeting_slo"])
    slo_pct = (meeting_slos / len(slo_stats) * 100) if slo_stats else 100

    # Cache performance
    cache_stats = await CacheMetrics.get_all_stats()
    avg_hit_rate = (
        sum(s["hit_rate"] for s in cache_stats) / len(cache_stats) if cache_stats else 0
    )

    # Circuit breaker
    cb_status = await openai_breaker.get_status()
    cb_healthy = cb_status["state"] == "closed"

    # Cost budget
    tracker = CostTracker(db)
    budget = await tracker.check_budget(auth.user_id, auth.org_id)
    budget_ok = not budget["over_budget"]

    # Overall health
    all_healthy = (
        slo_pct >= 80  # 80% of operations meeting SLO
        and avg_hit_rate >= 50  # 50% cache hit rate minimum
        and cb_healthy
        and budget_ok
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "slo_compliance_pct": round(slo_pct, 1),
        "cache_hit_rate_pct": round(avg_hit_rate, 1),
        "circuit_breaker_healthy": cb_healthy,
        "budget_ok": budget_ok,
        "details": {
            "slos_meeting_target": f"{meeting_slos}/{len(slo_stats)}",
            "cache_target": "70%",
            "circuit_breaker_state": cb_status["state"],
            "user_budget_remaining": budget["user_remaining"],
            "org_budget_remaining": budget["org_remaining"],
        },
    }
