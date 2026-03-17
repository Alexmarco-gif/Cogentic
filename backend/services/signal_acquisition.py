"""Signal acquisition service — orchestrates the full fetch→dedup→store pipeline.

This is the core service for Sprint 2. It:
1. Loads signal contracts from DB
2. Routes to the correct fetcher (API/RSS/Scraper/Social)
3. Deduplicates results
4. Extracts & normalizes
5. Stores as Signal records
6. Updates contract health status

Runs inside RQ workers — NOT in the API process.
"""

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db_context
from backend.models.signal_contract import SignalContract
from backend.repositories.signal import SignalRepository
from backend.repositories.signal_contract import SignalContractRepository
from backend.signals.fetchers import FetchError, get_fetcher
from backend.signals.processors.dedup import DedupProcessor
from backend.signals.processors.extractor import ExtractorProcessor

logger = logging.getLogger(__name__)

# Exponential backoff: retry delays in seconds
_BACKOFF_DELAYS = [60, 300, 1800]  # 1min, 5min, 30min


class SignalAcquisitionService:
    """Orchestrates the signal acquisition pipeline.

    Pipeline: Contract → Fetcher → Dedup → Extract → Store → Update Health

    Called by RQ job handlers, NOT directly from API endpoints.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.contract_repo = SignalContractRepository(db)
        self.signal_repo = SignalRepository(db)
        self.dedup = DedupProcessor(db)
        self.extractor = ExtractorProcessor()

    async def fetch_by_tier(self, tier: str) -> dict[str, Any]:
        """Fetch all active contracts in a given schedule tier.

        Args:
            tier: Schedule tier (realtime, standard, slow, daily)

        Returns:
            Summary dict with counts of fetched/failed/deduped signals.
        """
        contracts = await self.contract_repo.get_by_schedule_tier(tier)
        logger.info(f"Tier '{tier}': found {len(contracts)} active contracts")

        stats = {
            "tier": tier,
            "contracts_total": len(contracts),
            "contracts_succeeded": 0,
            "contracts_failed": 0,
            "signals_fetched": 0,
            "signals_deduped": 0,
            "signals_stored": 0,
        }

        for contract in contracts:
            try:
                result = await self.fetch_contract(contract)
                stats["signals_fetched"] += result["fetched"]
                stats["signals_deduped"] += result["deduped"]
                stats["signals_stored"] += result["stored"]
                stats["contracts_succeeded"] += 1
            except Exception as e:
                stats["contracts_failed"] += 1
                logger.error(
                    f"Failed to fetch contract {contract.id} ({contract.name}): {e}"
                )
                await self._handle_failure(contract, str(e))

        logger.info(
            f"Tier '{tier}' complete: "
            f"{stats['contracts_succeeded']}/{stats['contracts_total']} succeeded, "
            f"{stats['signals_stored']} new signals stored"
        )
        return stats

    async def fetch_contract(
        self,
        contract: SignalContract,
    ) -> dict[str, int]:
        """Execute the full pipeline for a single signal contract.

        Args:
            contract: The signal contract to fetch.

        Returns:
            Dict with fetched/deduped/stored counts.
        """
        logger.info(
            f"Fetching contract: {contract.name} "
            f"(type={contract.source_type}, url={contract.source_url[:80]})"
        )

        # 1. Get the right fetcher
        fetcher = get_fetcher(contract.source_type)

        try:
            # 2. Fetch raw results
            raw_results = await fetcher.fetch(
                source_url=contract.source_url,
                extraction_config=contract.extraction_config or {},
            )
        finally:
            await fetcher.close()

        # Handle fetch errors
        if isinstance(raw_results, FetchError):
            await self._handle_failure(contract, raw_results.message)
            raise RuntimeError(
                f"Fetch failed for {contract.name}: {raw_results.message}"
            )

        total_fetched = len(raw_results)

        # 3. Deduplicate
        unique_results = await self.dedup.filter_duplicates(raw_results)
        total_deduped = total_fetched - len(unique_results)

        # 4. Extract & normalize into signal dicts
        signal_dicts = self.extractor.process_batch(
            unique_results,
            contract_id=contract.id,  # type: ignore[arg-type]
            source_type=contract.source_type,
        )

        # 5. Bulk insert signals
        if signal_dicts:
            signals = await self.signal_repo.create_many(signal_dicts)
            total_stored = len(signals)

            # 5b. Enqueue refinement job for new signals (non-blocking)
            if signals:
                try:
                    signal_ids = [str(s.id) for s in signals]
                    from backend.job_queue import enqueue_job
                    from backend.jobs.refinement_job import refine_signals

                    enqueue_job(
                        refine_signals,
                        signal_ids,
                        queue_name="default",
                        job_timeout="15m",
                    )
                    logger.info(
                        f"Enqueued refinement for {len(signal_ids)} new signals"
                    )
                except Exception as e:
                    logger.error(f"Failed to enqueue refinement: {e}")

            # 5c. Deliver signals via webhook when delivery mode is webhook
            if contract.source_type == "webhook" and contract.source_url and signals:
                try:
                    from backend.job_handlers import send_webhook_notification

                    payload = {
                        "contract_id": str(contract.id),
                        "contract_name": contract.name,
                        "signal_count": len(signals),
                        "signal_ids": [str(s.id) for s in signals],
                    }
                    signing_secret = (contract.extraction_config or {}).get(
                        "webhook_secret"
                    )
                    await asyncio.to_thread(
                        send_webhook_notification,
                        contract.source_url,
                        "signals.created",
                        payload,
                        signing_secret,
                    )
                    logger.info(
                        f"Webhook delivery triggered for contract "
                        f"'{contract.name}': {len(signals)} signals"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to deliver webhook for contract {contract.id}: {e}"
                    )
        else:
            total_stored = 0

        # 6. Mark contract as successfully fetched
        await self.contract_repo.mark_fetched(contract.id)  # type: ignore[arg-type]

        logger.info(
            f"Contract '{contract.name}': "
            f"fetched={total_fetched}, deduped={total_deduped}, stored={total_stored}"
        )

        return {
            "fetched": total_fetched,
            "deduped": total_deduped,
            "stored": total_stored,
        }

    async def fetch_contract_by_id(self, contract_id: UUID) -> dict[str, Any]:
        """Fetch a single contract by ID (for manual/on-demand triggers).

        Args:
            contract_id: UUID of the signal contract to fetch.

        Returns:
            Result dict with counts.

        Raises:
            ValueError: If contract not found or inactive.
        """
        contract = await self.contract_repo.get(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")
        if not contract.is_active:
            raise ValueError(f"Contract {contract_id} is inactive")

        return await self.fetch_contract(contract)

    async def _handle_failure(
        self,
        contract: SignalContract,
        error_message: str,
    ):
        """Record a fetch failure with exponential backoff logic.

        After max_failures (default 3), contract status → "degraded".
        """
        await self.contract_repo.mark_failed(contract.id, error_message)  # type: ignore[arg-type]
        logger.warning(
            f"Contract '{contract.name}' failure #{contract.failure_count + 1}: "
            f"{error_message}"
        )

    async def check_health(self) -> dict[str, Any]:
        """Check health of all contracts, log degraded ones.

        Returns:
            Summary of contract health status.
        """
        degraded = await self.contract_repo.get_degraded_contracts()
        active = await self.contract_repo.get_active_contracts()

        if degraded:
            logger.warning(
                f"Health check: {len(degraded)} degraded contracts: "
                + ", ".join(c.name for c in degraded)
            )

        return {
            "active_contracts": len(active),
            "degraded_contracts": len(degraded),
            "degraded_names": [c.name for c in degraded],
        }


def run_fetch_by_tier(tier: str) -> dict[str, Any]:
    """Synchronous wrapper for RQ workers.

    RQ jobs must be sync functions, so this wraps the async pipeline.
    """

    async def _run():
        async with get_db_context() as db:
            service = SignalAcquisitionService(db)
            return await service.fetch_by_tier(tier)

    return asyncio.run(_run())


def run_fetch_contract(contract_id: str) -> dict[str, Any]:
    """Synchronous wrapper: fetch a single contract by ID."""

    async def _run():
        async with get_db_context() as db:
            service = SignalAcquisitionService(db)
            return await service.fetch_contract_by_id(UUID(contract_id))

    return asyncio.run(_run())


def run_health_check() -> dict[str, Any]:
    """Synchronous wrapper: run contract health check."""

    async def _run():
        async with get_db_context() as db:
            service = SignalAcquisitionService(db)
            return await service.check_health()

    return asyncio.run(_run())
