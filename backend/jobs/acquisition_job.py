"""Signal acquisition RQ job handlers.

These are the entry points for RQ workers. They are sync functions
that wrap the async SignalAcquisitionService.

Enqueued by the APScheduler (scheduler.py) or manual API triggers.
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def fetch_signals_by_tier(tier: str) -> dict[str, Any]:
    """Fetch all active contracts in a schedule tier.

    Called by APScheduler → RQ for periodic signal acquisition.

    Args:
        tier: One of "realtime", "standard", "slow", "daily"

    Returns:
        Stats dict with contract/signal counts.
    """
    logger.info(f"Starting signal fetch job for tier: {tier}")
    start = datetime.utcnow()

    from backend.services.signal_acquisition import run_fetch_by_tier

    result = run_fetch_by_tier(tier)

    duration = (datetime.utcnow() - start).total_seconds()
    result["duration_seconds"] = round(duration, 2)
    logger.info(f"Tier '{tier}' fetch completed in {duration:.1f}s: {result}")
    return result


def fetch_single_contract(contract_id: str) -> dict[str, Any]:
    """Fetch signals for a single contract (on-demand).

    Called by admin API endpoint for manual refresh.

    Args:
        contract_id: UUID string of the contract to fetch.

    Returns:
        Result dict with fetched/deduped/stored counts.
    """
    logger.info(f"Starting on-demand fetch for contract: {contract_id}")
    start = datetime.utcnow()

    from backend.services.signal_acquisition import run_fetch_contract

    result = run_fetch_contract(contract_id)

    duration = (datetime.utcnow() - start).total_seconds()
    result["duration_seconds"] = round(duration, 2)
    logger.info(f"Contract {contract_id} fetch completed in {duration:.1f}s: {result}")
    return result


def check_contract_health() -> dict[str, Any]:
    """Check health status of all signal contracts.

    Called periodically (every 30min) by APScheduler.
    Identifies degraded contracts that need attention.

    Returns:
        Health summary dict.
    """
    logger.info("Starting signal contract health check")

    from backend.services.signal_acquisition import run_health_check

    result = run_health_check()

    logger.info(f"Health check complete: {result}")
    return result
