"""Feedback-driven retraining loop.

Reads accumulated human feedback (entity approvals/rejections, signal
quality votes) and:
  1. Promotes/demotes Entity discovery_status so get_feedback_examples()
     picks up fresh calibration data on the next NER run.
  2. Writes a timestamped JSONL training snapshot to disk for offline
     ML model improvement (scoring models).
  3. Caches the rendered NER calibration block in Redis so extraction
     workers can fetch it without a DB round-trip.

Intended to run as a periodic RQ job (low-priority queue, every 6 h).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, update

from backend.database import AsyncSessionLocal
from backend.models.entity import Entity
from backend.models.user_feedback import UserFeedback
from backend.redis_client import get_redis_client
from backend.services.feedback_service import FeedbackService

logger = logging.getLogger(__name__)

# Redis key that EntityExtractionService workers can consume
_NER_CACHE_KEY = "ner:calibration:cache"
_NER_CACHE_TTL_S = 6 * 60 * 60  # 6 hours

# On-disk training snapshot directory (bind-mounted in Docker)
_TRAINING_DIR = Path(os.getenv("TRAINING_DATA_DIR", "/tmp/cogent_training"))


# ── Helpers ───────────────────────────────────────────────────────────────────


def _redis_set(key: str, value: str, ttl: int) -> None:
    """Fire-and-forget synchronous Redis write (safe in async ctx too)."""
    try:
        conn = get_redis_client()
        conn.setex(key, ttl, value)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis write failed for key=%s: %s", key, exc)


# ── Core async implementation ─────────────────────────────────────────────────


async def _promote_entity_feedback(
    db: Any,
    *,
    lookback_days: int = 30,
) -> dict[str, int]:
    """Apply pending entity feedback to Entity.discovery_status.

    • entity_relevant  → discovery_status = 'active'
    • entity_not_relevant → discovery_status = 'rejected'
    • expert_correction (target_type='entity') → discovery_status = 'active'
      (the human gave the correct label in feedback.context['correct_type'])

    Returns a summary dict with counts of approvals / rejections applied.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    result = await db.execute(
        select(UserFeedback).where(
            and_(
                UserFeedback.target_type == "entity",
                UserFeedback.created_at >= cutoff,
                UserFeedback.feedback_type.in_(
                    ["entity_relevant", "entity_not_relevant", "expert_correction"]
                ),
            )
        )
    )
    rows: list[UserFeedback] = result.scalars().all()

    approvals: list[UUID] = []
    rejections: list[UUID] = []
    corrections: list[tuple[UUID, str | None]] = []  # (entity_id, correct_type)

    for fb in rows:
        if fb.feedback_type == "entity_relevant":
            approvals.append(fb.target_id)
        elif fb.feedback_type == "entity_not_relevant":
            rejections.append(fb.target_id)
        elif fb.feedback_type == "expert_correction":
            correct_type = (fb.context or {}).get("correct_type")
            corrections.append((fb.target_id, correct_type))

    # Apply in bulk where possible
    if approvals:
        await db.execute(
            update(Entity)
            .where(Entity.id.in_(approvals))
            .values(discovery_status="active")
        )

    if rejections:
        await db.execute(
            update(Entity)
            .where(Entity.id.in_(rejections))
            .values(discovery_status="rejected")
        )

    # Corrections with an explicit type overwrite both status and entity_type
    for entity_id, correct_type in corrections:
        values: dict[str, Any] = {"discovery_status": "active"}
        if correct_type:
            values["entity_type"] = correct_type
        await db.execute(
            update(Entity).where(Entity.id == entity_id).values(**values)
        )

    await db.commit()

    return {
        "approvals": len(approvals),
        "rejections": len(rejections),
        "corrections": len(corrections),
    }


async def _write_training_snapshot(db: Any) -> Path | None:
    """Persist a JSONL signal-quality training snapshot for ML retraining.

    The snapshot is written to TRAINING_DATA_DIR so it can be consumed
    by any offline model training pipeline without coupling to the API.
    """
    svc = FeedbackService(db)
    training_data = await svc.get_signal_quality_training_data(
        min_votes=3,
        lookback_days=180,
        limit=10_000,
    )

    if not training_data:
        logger.info("No signal quality training data available — skipping snapshot.")
        return None

    _TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = _TRAINING_DIR / f"signal_quality_{ts}.jsonl"

    with out_path.open("w", encoding="utf-8") as fh:
        for record in training_data:
            fh.write(json.dumps(record, default=str) + "\n")

    logger.info(
        "Wrote %d training examples to %s", len(training_data), out_path
    )
    return out_path


async def _refresh_ner_cache(db: Any) -> str:
    """Rebuild and cache the NER calibration block in Redis.

    EntityExtractionService._build_system_prompt() can call
    get_feedback_examples() which hits the DB.  This method pre-warms
    the Redis cache so workers don't all hit Postgres at once.
    """
    from backend.ai.entity_extraction import EntityExtractionService

    calibration_block = await EntityExtractionService.get_feedback_examples(
        db, limit=20
    )
    if calibration_block:
        _redis_set(_NER_CACHE_KEY, calibration_block, _NER_CACHE_TTL_S)
        logger.info(
            "NER calibration cache refreshed (%d chars).", len(calibration_block)
        )
    else:
        logger.info("No feedback examples available — NER cache not updated.")

    return calibration_block


async def _run_retraining_async(
    *,
    lookback_days: int = 30,
    write_snapshot: bool = True,
) -> dict[str, Any]:
    """Full retraining cycle — call within an async context."""
    async with AsyncSessionLocal() as db:
        # 1. Apply entity feedback → update Entity statuses
        entity_stats = await _promote_entity_feedback(db, lookback_days=lookback_days)
        logger.info("Entity feedback applied: %s", entity_stats)

        # 2. Write JSONL training snapshot
        snapshot_path: str | None = None
        if write_snapshot:
            path = await _write_training_snapshot(db)
            snapshot_path = str(path) if path else None

        # 3. Refresh NER calibration block in Redis
        calibration_block = await _refresh_ner_cache(db)

    return {
        "entity_promotions": entity_stats,
        "snapshot_path": snapshot_path,
        "ner_cache_refreshed": bool(calibration_block),
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Public RQ job entry-point ─────────────────────────────────────────────────


def run_feedback_retraining_job(
    *,
    lookback_days: int = 30,
    write_snapshot: bool = True,
) -> dict[str, Any]:
    """RQ-schedulable synchronous wrapper for the retraining cycle.

    Enqueue on the low-priority queue every 6 hours:

        from backend.job_queue import get_low_priority_queue
        from backend.services.feedback_retraining import run_feedback_retraining_job

        q = get_low_priority_queue()
        q.enqueue(run_feedback_retraining_job, lookback_days=30, job_timeout=600)
    """
    logger.info(
        "Starting feedback retraining job (lookback=%d days, snapshot=%s)",
        lookback_days,
        write_snapshot,
    )
    result = asyncio.run(
        _run_retraining_async(
            lookback_days=lookback_days,
            write_snapshot=write_snapshot,
        )
    )
    logger.info("Feedback retraining complete: %s", result)
    return result
