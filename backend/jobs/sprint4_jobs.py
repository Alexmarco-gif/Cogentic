"""Sprint 4 RQ job handlers — Briefs + Recommendations.

Entry points for RQ workers. Sync functions that wrap async services.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ── Brief Refresh Jobs ───────────────────────────────────────────────


def refresh_all_briefs() -> dict[str, Any]:
    """Check and refresh all stale published briefs.

    Called periodically (every 2 hours) by scheduler.
    Rate-limited internally: max 1 refresh per brief per hour.

    Returns:
        Batch refresh summary dict.
    """
    logger.info("Starting brief refresh check job")
    start = datetime.now(timezone.utc)

    from backend.briefs.refresh import run_brief_refresh_check

    result = run_brief_refresh_check()

    duration = (datetime.now(timezone.utc) - start).total_seconds()
    logger.info(f"Brief refresh check completed in {duration:.1f}s: {result}")
    return result


def refresh_single_brief(brief_id: str) -> dict[str, Any]:
    """Refresh a single brief (on-demand or after new signals).

    Args:
        brief_id: UUID string of the brief.

    Returns:
        Refresh result dict.
    """
    logger.info(f"Starting single brief refresh for {brief_id}")

    from backend.briefs.refresh import run_single_brief_refresh

    result = run_single_brief_refresh(brief_id)
    logger.info(f"Brief refresh for {brief_id}: {result}")
    return result


# ── Recommendation Jobs ──────────────────────────────────────────────


def generate_recommendations(
    limit: int = 100,
    min_confidence: float = 0.60,
) -> dict[str, Any]:
    """Generate recommendations in batch.

    Called after refinement pipeline completes, or periodically.
    Processes signals with embeddings above confidence threshold.

    Args:
        limit: Max signals to process.
        min_confidence: Only process signals above this threshold.

    Returns:
        Batch summary dict.
    """
    logger.info(f"Starting recommendation batch (limit={limit})")
    start = datetime.now(timezone.utc)

    from backend.services.recommendation import run_recommendation_batch

    result = run_recommendation_batch(limit=limit, min_confidence=min_confidence)

    duration = (datetime.now(timezone.utc) - start).total_seconds()
    result["duration_seconds"] = round(duration, 2)
    logger.info(f"Recommendation batch completed in {duration:.1f}s: {result}")
    return result
