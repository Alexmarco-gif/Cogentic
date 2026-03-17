"""Source discovery periodic job — auto-activates high-confidence recommended sources.

Runs as an RQ scheduled job (e.g., every 6 hours). Checks for recommended
sources that exceed auto-activation thresholds and creates live contracts
for them automatically — no human intervention needed.

This is the "fully autonomous" tier of the living contracts system.
Sources below the auto-activate threshold stay in "recommended" status
for manual review via the /api/v1/discovered-sources/recommended endpoint.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def auto_activate_sources(dry_run: bool = False) -> dict[str, Any]:
    """Check recommended sources and auto-activate those exceeding thresholds.

    Args:
        dry_run: If True, report what would be activated without actually doing it.

    Returns:
        Summary of sources checked, activated, and skipped.
    """
    logger.info("Starting source auto-activation check")
    start = datetime.now(timezone.utc)

    import asyncio

    from backend.database import get_db_context
    from backend.services.source_discovery import (
        AUTO_ACTIVATE_MIN_MENTIONS,
        AUTO_ACTIVATE_MIN_RELEVANCE,
        SourceDiscoveryService,
    )

    async def _run() -> dict[str, Any]:
        async with get_db_context() as db:
            service = SourceDiscoveryService(db)

            # Get all recommended sources
            recommended = await service.get_recommended(limit=100)

            checked = 0
            activated = 0
            skipped = 0
            activated_list: list[dict] = []

            for source in recommended:
                checked += 1

                if (
                    source.mention_count >= AUTO_ACTIVATE_MIN_MENTIONS
                    and source.relevance_score >= AUTO_ACTIVATE_MIN_RELEVANCE
                ):
                    if dry_run:
                        activated_list.append(
                            {
                                "domain": source.domain,
                                "url": source.url,
                                "mentions": source.mention_count,
                                "relevance": round(source.relevance_score, 3),
                                "action": "would_activate",
                            }
                        )
                        activated += 1
                        continue

                    # Infer industry from the first signal
                    industry_id = await service._infer_industry_id(
                        source.first_seen_signal_id
                    )
                    if not industry_id:
                        logger.warning(
                            f"Skipping {source.domain}: cannot infer industry"
                        )
                        skipped += 1
                        continue

                    contract = await service.activate_source(
                        source.id,
                        industry_id=industry_id,
                    )
                    if contract:
                        activated += 1
                        activated_list.append(
                            {
                                "domain": source.domain,
                                "url": source.url,
                                "contract_id": str(contract.id),
                                "schedule_tier": contract.schedule_tier,
                            }
                        )
                    else:
                        skipped += 1
                else:
                    skipped += 1

            await db.commit()

            return {
                "checked": checked,
                "activated": activated,
                "skipped": skipped,
                "dry_run": dry_run,
                "details": activated_list,
            }

    result = asyncio.run(_run())

    duration = (datetime.now(timezone.utc) - start).total_seconds()
    result["duration_seconds"] = round(duration, 2)
    logger.info(
        f"Source auto-activation complete in {duration:.1f}s: "
        f"{result['activated']} activated, {result['skipped']} skipped"
    )
    return result


def source_discovery_stats() -> dict[str, Any]:
    """Get current source discovery statistics (for monitoring dashboards).

    Returns:
        Stats dict with counts by status.
    """
    import asyncio

    from backend.database import get_db_context
    from backend.services.source_discovery import SourceDiscoveryService

    async def _run() -> dict[str, Any]:
        async with get_db_context() as db:
            service = SourceDiscoveryService(db)
            return await service.get_stats()

    return asyncio.run(_run())
