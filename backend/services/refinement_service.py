"""Signal refinement service — orchestrates embedding + entity resolution + ML scoring + causal intelligence.

Called after the acquisition pipeline stores new signals.
Enriches signals with:
  1. Embeddings (OpenAI text-embedding-3-small → pgvector)
  2. Entity links (semantic + fuzzy matching → signal_entities)
  3. ML scores (anomaly, trending, confidence → signal_scores)
  4. Semantic dedup check (cosine similarity > 0.95)
  5. Causal event extraction + edge detection (intelligence moat)

Runs as RQ job (non-blocking, async).
"""

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.embeddings import EmbeddingService
from backend.database import get_db_context
from backend.ml.entity_resolver import EntityResolver
from backend.ml.scoring import ScoringService
from backend.models.signal import Signal
from backend.repositories.signal import SignalRepository
from backend.signals.processors.dedup import DedupProcessor

logger = logging.getLogger(__name__)


class RefinementService:
    """Orchestrates the signal refinement pipeline.

    Pipeline per signal:
      1. Generate embedding → store on Signal.embedding
      2. Semantic dedup check → skip if near-duplicate
      3. Resolve entities → create SignalEntity links
      4. Run ML scoring → create SignalScore records + update confidence
      5. Extract causal event → create CausalEvent + detect edges

    Called by RQ jobs after signal acquisition stores new signals.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.signal_repo = SignalRepository(db)
        self.embedding_service = EmbeddingService(db)
        self.entity_resolver = EntityResolver(db)
        self.scoring_service = ScoringService(db)
        self.dedup = DedupProcessor(db)
        # Intelligence moat services
        self._causal_service = None
        self._regulatory_service = None

    @property
    def causal_service(self):
        """Lazy-load causal intelligence service."""
        if self._causal_service is None:
            from backend.services.causal_intelligence import CausalIntelligenceService
            self._causal_service = CausalIntelligenceService(self.db)
        return self._causal_service

    @property
    def regulatory_service(self):
        """Lazy-load regulatory intelligence service."""
        if self._regulatory_service is None:
            from backend.services.regulatory_intelligence import RegulatoryIntelligenceService
            self._regulatory_service = RegulatoryIntelligenceService(self.db)
        return self._regulatory_service

    async def refine_signal(self, signal: Signal) -> dict[str, Any]:
        """Run the full refinement pipeline on a single signal.

        Args:
            signal: Signal ORM instance (freshly acquired).

        Returns:
            Refinement result dict.
        """
        result = {
            "signal_id": str(signal.id),
            "embedded": False,
            "semantic_duplicate": False,
            "entities_linked": 0,
            "scores": {},
        }

        # Step 1: Generate embedding
        try:
            embedding = await self.embedding_service.generate_signal_embedding(signal)
            result["embedded"] = True
        except Exception as e:
            logger.error(f"Embedding failed for signal {signal.id}: {e}")
            embedding = None

        # Step 2: Semantic dedup (Layer 2)
        if embedding and any(v != 0.0 for v in embedding):
            is_dup = await self.dedup.is_semantic_duplicate(embedding)
            if is_dup:
                result["semantic_duplicate"] = True
                logger.info(f"Signal {signal.id} is a semantic duplicate, skipping")
                # Mark duplicate with zero confidence so it's filtered out
                signal.confidence = 0.0
                await self.db.flush()
                return result

        # Step 3: Entity resolution
        try:
            links = await self.entity_resolver.resolve_signal(signal)
            result["entities_linked"] = len(links)
        except Exception as e:
            logger.error(f"Entity resolution failed for signal {signal.id}: {e}")

        # Step 4: ML scoring
        try:
            scores = await self.scoring_service.score_signal(signal)
            result["scores"] = scores

            # Persist scores
            from backend.repositories.signal_score import SignalScoreRepository
            score_repo = SignalScoreRepository(self.db)

            for score_type, score_value in scores.items():
                await score_repo.upsert_score(
                    signal_id=signal.id,
                    score_type=score_type,
                    score_value=round(score_value, 4),
                )

            # Update signal confidence with calibrated value
            if "confidence" in scores:
                signal.confidence = round(scores["confidence"], 4)
                await self.db.flush()

        except Exception as e:
            logger.error(f"ML scoring failed for signal {signal.id}: {e}")

        # Step 5: Causal event extraction (intelligence moat)
        try:
            event = await self.causal_service.extract_event_from_signal(signal)
            result["causal_event_id"] = str(event.id)
            result["causal_event_type"] = event.event_type

            # Detect causal edges to prior events
            edges = await self.causal_service.detect_causal_edges(event)
            result["causal_edges_detected"] = len(edges)
        except Exception as e:
            logger.debug(f"Causal extraction skipped for signal {signal.id}: {e}")
            result["causal_event_id"] = None
            result["causal_edges_detected"] = 0

        # Step 6: Regulatory event extraction (contextual intelligence)
        try:
            reg_event = await self.regulatory_service.extract_regulatory_event_from_signal(signal)
            if reg_event:
                result["regulatory_event_id"] = str(reg_event.id)
                result["regulatory_event_type"] = reg_event.event_type
        except Exception as e:
            logger.debug(f"Regulatory extraction skipped for signal {signal.id}: {e}")
            result["regulatory_event_id"] = None

        return result

    async def refine_batch(self, signal_ids: list[UUID]) -> dict[str, Any]:
        """Refine a batch of signals by their IDs.

        Args:
            signal_ids: List of signal UUIDs to refine.

        Returns:
            Batch refinement summary.
        """
        start = time.monotonic()

        signals = await self.signal_repo.get_by_ids(signal_ids)
        if not signals:
            return {"refined": 0, "errors": 0, "duplicates": 0}

        refined = 0
        errors = 0
        duplicates = 0

        # Step 1: Batch-embed all signals first (more efficient)
        try:
            unembedded = [s for s in signals if s.embedding is None]
            if unembedded:
                await self.embedding_service.batch_embed_signals(unembedded)
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")

        # Steps 2-4: Process each signal
        for signal in signals:
            try:
                result = await self.refine_signal(signal)

                if result["semantic_duplicate"]:
                    duplicates += 1
                else:
                    refined += 1

            except Exception as e:
                errors += 1
                logger.error(f"Refinement failed for signal {signal.id}: {e}")

        duration_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            f"Batch refinement complete: "
            f"{refined} refined, {duplicates} duplicates, "
            f"{errors} errors, {duration_ms}ms"
        )

        return {
            "total": len(signals),
            "refined": refined,
            "duplicates": duplicates,
            "errors": errors,
            "duration_ms": duration_ms,
        }

    async def refine_unprocessed(
        self,
        *,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Find and refine signals that haven't been embedded yet.

        Useful for batch catchup processing.

        Args:
            limit: Max signals to process in one run.

        Returns:
            Batch refinement summary.
        """
        from sqlalchemy import select

        result = await self.db.execute(
            select(Signal.id)
            .where(
                Signal.embedding.is_(None),
                Signal.confidence > 0.0,
            )
            .order_by(Signal.created_at.desc())
            .limit(limit)
        )
        signal_ids = [row[0] for row in result.all()]

        if not signal_ids:
            logger.info("No unprocessed signals found")
            return {"refined": 0, "errors": 0, "duplicates": 0}

        logger.info(f"Found {len(signal_ids)} unprocessed signals to refine")
        return await self.refine_batch(signal_ids)


# ── Synchronous wrappers for RQ workers ──────────────────────────────


def run_refine_batch(signal_ids: list[str]) -> dict[str, Any]:
    """Sync wrapper: refine a batch of signals by ID."""

    async def _run():
        async with get_db_context() as db:
            service = RefinementService(db)
            uuids = [UUID(sid) for sid in signal_ids]
            return await service.refine_batch(uuids)

    return asyncio.run(_run())


def run_refine_unprocessed(limit: int = 100) -> dict[str, Any]:
    """Sync wrapper: refine all unprocessed signals."""

    async def _run():
        async with get_db_context() as db:
            service = RefinementService(db)
            return await service.refine_unprocessed(limit=limit)

    return asyncio.run(_run())
