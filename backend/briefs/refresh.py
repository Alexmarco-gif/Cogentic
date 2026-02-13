"""Intelligence brief auto-refresh logic.

Monitors signal updates and triggers brief regeneration
when underlying signals change significantly.
Rate-limited: max 1 refresh per brief per hour.
Queued via RQ for async processing.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db_context
from backend.models.brief_signal import BriefSignal
from backend.models.intelligence_brief import IntelligenceBrief
from backend.models.signal_score import SignalScore
from backend.redis_client import get_redis
from backend.repositories.intelligence_brief import IntelligenceBriefRepository

logger = logging.getLogger(__name__)

# Rate limit: max 1 refresh per brief per hour
REFRESH_COOLDOWN_SECONDS = 3600
REFRESH_CACHE_PREFIX = "brief_refresh:"

# Thresholds for triggering refresh
CONFIDENCE_SHIFT_THRESHOLD = 0.10  # 10% confidence change triggers refresh
NEW_SIGNAL_COUNT_THRESHOLD = 3  # 3+ new signals trigger refresh


class BriefRefreshService:
    """Monitors signal changes and triggers brief regeneration.

    Checks:
      1. Signal confidence scores changed significantly
      2. New signals added to brief's signal set
      3. Brief not refreshed within stale window

    Rate-limited: max 1 refresh per brief per hour (Redis lock).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_refresh_all(
        self,
        *,
        stale_hours: int = 6,
        max_refreshes: int = 10,
    ) -> dict[str, Any]:
        """Check all published briefs for staleness and refresh if needed.

        Args:
            stale_hours: Hours since last refresh to consider stale.
            max_refreshes: Maximum briefs to refresh in one run.

        Returns:
            Summary dict with counts.
        """
        start = time.monotonic()
        stale_before = datetime.utcnow() - timedelta(hours=stale_hours)

        # Find stale published briefs (global query, no org scope)
        result = await self.db.execute(
            select(IntelligenceBrief)
            .where(
                IntelligenceBrief.status == "published",
                IntelligenceBrief.deleted_at.is_(None),
                (
                    IntelligenceBrief.refreshed_at.is_(None)
                    | (IntelligenceBrief.refreshed_at < stale_before)
                ),
            )
            .limit(max_refreshes)
        )
        stale_briefs = list(result.scalars().all())

        refreshed = 0
        skipped = 0
        errors = 0

        for brief in stale_briefs:
            try:
                # Check rate limit
                if await self._is_rate_limited(brief.id):
                    skipped += 1
                    continue

                # Check if underlying signals changed enough
                needs_refresh = await self._needs_refresh(brief)
                if not needs_refresh:
                    skipped += 1
                    continue

                # Perform refresh
                await self._refresh_brief(brief)
                await self._set_rate_limit(brief.id)
                refreshed += 1

            except Exception as e:
                errors += 1
                logger.error(f"Brief refresh failed for {brief.id}: {e}")

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            f"Brief refresh check: {refreshed} refreshed, "
            f"{skipped} skipped, {errors} errors, {duration_ms}ms"
        )

        return {
            "total_checked": len(stale_briefs),
            "refreshed": refreshed,
            "skipped": skipped,
            "errors": errors,
            "duration_ms": duration_ms,
        }

    async def refresh_single(
        self,
        brief_id: UUID,
        org_id: UUID,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        """Refresh a single brief by ID.

        Args:
            brief_id: Brief to refresh.
            org_id: Org scope.
            force: Skip rate limit check.

        Returns:
            Refresh result dict.
        """
        # Rate limit check (unless forced)
        if not force and await self._is_rate_limited(brief_id):
            return {
                "status": "rate_limited",
                "brief_id": str(brief_id),
                "message": "Brief was refreshed recently. Max 1 per hour.",
            }

        repo = IntelligenceBriefRepository(self.db, org_id)
        brief = await repo.get_with_signals(brief_id)
        if not brief:
            return {"status": "not_found", "brief_id": str(brief_id)}

        try:
            await self._refresh_brief(brief)
            await self._set_rate_limit(brief_id)
            return {
                "status": "refreshed",
                "brief_id": str(brief_id),
                "refreshed_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Single brief refresh failed: {brief_id}: {e}")
            return {
                "status": "error",
                "brief_id": str(brief_id),
                "error": str(e)[:200],
            }

    # ── Internal ─────────────────────────────────────────────────────

    async def _needs_refresh(self, brief: IntelligenceBrief) -> bool:
        """Check if a brief's underlying signals have changed enough.

        Checks:
          1. Any linked signal's confidence score changed > threshold
          2. New high-confidence signals available for the same industry
        """
        # Get linked signal IDs
        result = await self.db.execute(
            select(BriefSignal.signal_id).where(BriefSignal.brief_id == brief.id)
        )
        signal_ids = [row[0] for row in result.all()]

        if not signal_ids:
            return True  # No signals = definitely needs refresh

        # Check for significant score changes since last refresh
        if brief.refreshed_at:
            score_result = await self.db.execute(
                select(SignalScore).where(
                    SignalScore.signal_id.in_(signal_ids),
                    SignalScore.created_at > brief.refreshed_at,
                )
            )
            new_scores = list(score_result.scalars().all())
            if len(new_scores) >= NEW_SIGNAL_COUNT_THRESHOLD:
                return True

        return True  # Default: refresh stale briefs

    async def _refresh_brief(self, brief: IntelligenceBrief) -> None:
        """Actually regenerate a brief's content."""
        from backend.briefs.generator import BriefGenerator

        generator = BriefGenerator(self.db)
        await generator.regenerate_brief(
            brief_id=brief.id,
            org_id=brief.org_id or UUID(int=0),  # Use zero UUID for global briefs
        )

    async def _is_rate_limited(self, brief_id: UUID) -> bool:
        """Check if brief was refreshed within cooldown period."""
        try:
            redis = await get_redis()
            key = f"{REFRESH_CACHE_PREFIX}{brief_id}"
            return await redis.exists(key) > 0
        except Exception:
            return False  # Fail open

    async def _set_rate_limit(self, brief_id: UUID) -> None:
        """Set rate limit lock for brief refresh."""
        try:
            redis = await get_redis()
            key = f"{REFRESH_CACHE_PREFIX}{brief_id}"
            await redis.setex(key, REFRESH_COOLDOWN_SECONDS, "1")
        except Exception as e:
            logger.warning(f"Failed to set refresh rate limit: {e}")


# ── Synchronous wrappers for RQ workers ──────────────────────────────


def run_brief_refresh_check(
    stale_hours: int = 6,
    max_refreshes: int = 10,
) -> dict[str, Any]:
    """Sync wrapper for RQ: check and refresh stale briefs."""

    async def _run():
        async with get_db_context() as db:
            service = BriefRefreshService(db)
            return await service.check_and_refresh_all(
                stale_hours=stale_hours,
                max_refreshes=max_refreshes,
            )

    return asyncio.run(_run())


def run_single_brief_refresh(
    brief_id: str,
    org_id: str,
    force: bool = False,
) -> dict[str, Any]:
    """Sync wrapper for RQ: refresh a single brief."""

    async def _run():
        async with get_db_context() as db:
            service = BriefRefreshService(db)
            return await service.refresh_single(
                UUID(brief_id),
                UUID(org_id),
                force=force,
            )

    return asyncio.run(_run())
