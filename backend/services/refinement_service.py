"""Signal refinement service — orchestrates embedding + NER + entity resolution + ML scoring + causal intelligence.

Called after the acquisition pipeline stores new signals.
Enriches signals with:
  1. Embeddings (OpenAI text-embedding-3-small → pgvector)
  2. Semantic dedup check (cosine similarity > 0.95)
  3. LLM entity extraction (GPT-4o NER — discovers entities, prices, locations, sources)
  4. Entity resolution with auto-creation (confidence-tiered: >0.8 active, 0.5-0.8 pending)
  5. Structured data enrichment (prices, geographic, sources → extracted_data)
  6. Source discovery (URLs referenced in signals → discovered_sources)
  7. ML scores (anomaly, trending, confidence → signal_scores)
  8. Causal event extraction + edge detection (intelligence moat)

Runs as RQ job (non-blocking, async).
"""

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.embeddings import EmbeddingService
from backend.ai.entity_extraction import EntityExtractionService, ExtractionResult
from backend.database import get_db_context
from backend.models.market_data import MarketDataPoint
from backend.models.signal import Signal
from backend.repositories.signal import SignalRepository
from backend.signals.processors.dedup import DedupProcessor

logger = logging.getLogger(__name__)


class RefinementService:
    """Orchestrates the signal refinement pipeline.

    Pipeline per signal:
      1. Generate embedding → store on Signal.embedding
      2. Semantic dedup check → skip if near-duplicate
      3. LLM entity extraction (NER) → discover entities, prices, locations, sources
      4. Entity resolution with auto-creation → resolve or create entities
      5. Enrich signal extracted_data with structured data
      6. Track discovered sources for living contracts
      7. Run ML scoring → create SignalScore records + update confidence
      8. Extract causal event → create CausalEvent + detect edges

    Called by RQ jobs after signal acquisition stores new signals.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.signal_repo = SignalRepository(db)
        self.embedding_service = EmbeddingService(db)
        self.dedup = DedupProcessor(db)
        self.entity_extraction = EntityExtractionService()
        # Lazy-loaded services
        self._scoring_service = None
        self._entity_resolution_service = None
        self._source_discovery_service = None
        self._causal_service = None
        self._regulatory_service = None

    @property
    def scoring_service(self):
        """Lazy-load ML scoring so worker startup doesn't require ML runtimes."""
        if self._scoring_service is None:
            from backend.ml.scoring import ScoringService

            self._scoring_service = ScoringService(self.db)
        return self._scoring_service

    @property
    def entity_resolution_service(self):
        """Lazy-load entity resolution service (rich version with auto-create)."""
        if self._entity_resolution_service is None:
            from backend.services.entity_resolution import EntityResolutionService

            self._entity_resolution_service = EntityResolutionService(self.db)
        return self._entity_resolution_service

    @property
    def source_discovery_service(self):
        """Lazy-load source discovery service."""
        if self._source_discovery_service is None:
            from backend.services.source_discovery import SourceDiscoveryService

            self._source_discovery_service = SourceDiscoveryService(self.db)
        return self._source_discovery_service

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
            from backend.services.regulatory_intelligence import (
                RegulatoryIntelligenceService,
            )

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
            "entities_created": 0,
            "numeric_data_extracted": 0,
            "market_data_points_created": 0,
            "sources_discovered": 0,
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

        # Step 3: LLM Entity Extraction (NER) — discovers entities, prices, locations, sources
        extraction: ExtractionResult | None = None
        try:
            # Load feedback from reviewed entities once per service instance
            if not hasattr(self, "_feedback_examples"):
                self._feedback_examples = (
                    await EntityExtractionService.get_feedback_examples(
                        self.db, limit=10
                    )
                )

            # Infer country: extracted_data > org.default_country > None
            signal_country = None
            if signal.extracted_data:
                signal_country = signal.extracted_data.get("country_code")
            if not signal_country and signal.org_id:
                # Load org default_country for proper regional NER context
                from sqlalchemy import select as sa_select

                from backend.models.organization import Organization

                org_row = await self.db.execute(
                    sa_select(Organization.default_country).where(
                        Organization.id == signal.org_id
                    )
                )
                org_country = org_row.scalar_one_or_none()
                if org_country:
                    signal_country = org_country

            extraction = await self.entity_extraction.extract(
                title=signal.title,
                content="\n\n".join(
                    p for p in [signal.summary, signal.raw_content] if p
                )
                or None,
                country=signal_country,
                feedback=self._feedback_examples or None,
            )
        except Exception as e:
            logger.error(f"Entity extraction (NER) failed for signal {signal.id}: {e}")

        # Step 4: Entity resolution with auto-creation
        if extraction and extraction.entities:
            try:
                linked, created = await self._resolve_extracted_entities(
                    signal, extraction
                )
                result["entities_linked"] = linked
                result["entities_created"] = created
            except Exception as e:
                logger.error(f"Entity resolution failed for signal {signal.id}: {e}")

        # Step 5: Enrich signal extracted_data with structured data
        if extraction:
            try:
                self._enrich_signal_data(signal, extraction)
                result["numeric_data_extracted"] = len(extraction.numeric_data)
                await self.db.flush()

                # Persist MarketDataPoint rows for time-series queries
                if extraction.numeric_data:
                    mdp_list = await self._persist_market_data_with_list(
                        signal, extraction
                    )
                    result["market_data_points_created"] = len(mdp_list)

                    # Run change detection on each new data point
                    if mdp_list:
                        alerts_created = await self._run_change_detection(mdp_list)
                        result["alerts_created"] = alerts_created
            except Exception as e:
                logger.error(
                    f"Structured data enrichment failed for signal {signal.id}: {e}"
                )

        # Step 6: Source discovery — track referenced URLs for living contracts
        if extraction and extraction.sources:
            try:
                discovered = await self.source_discovery_service.track_sources(
                    extraction.sources, signal_id=signal.id
                )
                result["sources_discovered"] = discovered
            except Exception as e:
                logger.error(f"Source discovery failed for signal {signal.id}: {e}")

        # Step 7: ML scoring
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

        # Step 8: Causal event extraction (intelligence moat)
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

        # Step 9: Regulatory event extraction (contextual intelligence)
        try:
            reg_event = (
                await self.regulatory_service.extract_regulatory_event_from_signal(
                    signal
                )
            )
            if reg_event:
                result["regulatory_event_id"] = str(reg_event.id)
                result["regulatory_event_type"] = reg_event.event_type
        except Exception as e:
            logger.debug(f"Regulatory extraction skipped for signal {signal.id}: {e}")
            result["regulatory_event_id"] = None

        # Step 10: Persist provenance / lineage audit trail
        try:
            signal.provenance = {
                "pipeline_version": "2.0",
                "ner_model": extraction.extraction_model if extraction else None,
                "ner_tokens": extraction.tokens_used if extraction else 0,
                "country_context": signal_country,
                "entities_found": len(extraction.entities) if extraction else 0,
                "numeric_data_found": len(extraction.numeric_data) if extraction else 0,
                "sources_found": len(extraction.sources) if extraction else 0,
                "score_breakdown": result.get("scores", {}),
                "stages": {
                    "embedded": result.get("embedded", False),
                    "semantic_dedup": result.get("semantic_duplicate", False),
                    "entities_linked": result.get("entities_linked", 0),
                    "entities_created": result.get("entities_created", 0),
                    "market_data_points": result.get("market_data_points_created", 0),
                    "sources_discovered": result.get("sources_discovered", 0),
                    "causal_event_id": result.get("causal_event_id"),
                    "regulatory_event_id": result.get("regulatory_event_id"),
                },
                "refined_at": time.time(),
            }
            await self.db.flush()
        except Exception as e:
            logger.warning(f"Provenance write failed for signal {signal.id}: {e}")

        return result

    # ── NER → Entity Resolution Integration ──────────────────────────

    async def _resolve_extracted_entities(
        self,
        signal: Signal,
        extraction: ExtractionResult,
    ) -> tuple[int, int]:
        """Resolve NER-extracted entities via EntityResolutionService.

        Uses confidence-tiered auto-creation:
          - NER confidence >= 0.8 → auto-create with discovery_status='active'
          - NER confidence 0.5-0.8 → auto-create with discovery_status='pending_review'
          - NER confidence < 0.5 → discard (already filtered in extraction)

        Returns:
            Tuple of (entities_linked, entities_created).
        """
        from backend.models.signal_entity import SignalEntity

        linked = 0
        created = 0

        for mention in extraction.entities:
            # Build context from signal text for embedding-based matching
            context = f"{signal.title or ''} {signal.summary or ''}"[:500]

            entity, confidence = await self.entity_resolution_service.resolve(
                mention.name,
                entity_type=mention.entity_type,
                industry_id=signal.contract.industry_id if signal.contract else None,
                context=context,
                min_confidence=0.65,
                auto_create=True,  # Enable dynamic entity discovery
            )

            if not entity:
                continue

            # Set discovery fields on newly created entities
            if confidence == 0.6:  # Auto-created (EntityResolutionService returns 0.6)
                created += 1
                # Determine discovery_status based on NER confidence
                if mention.confidence >= 0.8:
                    entity.discovery_status = "active"
                else:
                    entity.discovery_status = "pending_review"
                entity.discovery_source = "auto_extracted"

                # Add NER-discovered aliases
                for alias in mention.aliases:
                    try:
                        await self.entity_resolution_service.add_alias(
                            entity.id,
                            alias,
                            alias_type="trading_name",
                            source="ner_extraction",
                            confidence=mention.confidence,
                        )
                    except Exception:
                        pass  # Duplicate alias, skip

                # Generate embedding for the new entity
                try:
                    await self.embedding_service.generate_entity_embedding(entity)
                except Exception as e:
                    logger.debug(f"Embedding for new entity {entity.name} failed: {e}")

                await self.db.flush()

            # Create signal-entity link
            from sqlalchemy import select

            existing = await self.db.execute(
                select(SignalEntity).where(
                    SignalEntity.signal_id == signal.id,
                    SignalEntity.entity_id == entity.id,
                )
            )
            if not existing.scalar_one_or_none():
                link = SignalEntity(
                    signal_id=signal.id,
                    entity_id=entity.id,
                    relevance_score=round(max(confidence, mention.confidence), 4),
                )
                self.db.add(link)
                linked += 1

        if linked or created:
            await self.db.flush()
            logger.info(
                f"Signal {signal.id}: linked {linked} entities, "
                f"created {created} new entities via NER"
            )

        return linked, created

    # ── Structured Data Enrichment ───────────────────────────────────

    @staticmethod
    def _enrich_signal_data(signal: Signal, extraction: ExtractionResult) -> None:
        """Enrich signal.extracted_data with structured NER output.

        Adds typed, queryable data instead of leaving intelligence
        buried in unstructured text.
        """
        data = dict(signal.extracted_data or {})

        # Add structured numeric data (prices, rates, volumes)
        if extraction.numeric_data:
            data["numeric_data"] = [
                {
                    "value": n.value,
                    "unit": n.unit,
                    "metric": n.metric,
                    "currency": n.currency,
                    "context": n.context,
                }
                for n in extraction.numeric_data
            ]

        # Add structured geographic data
        if extraction.geographic:
            data["geographic"] = [
                {
                    "name": g.name,
                    "type": g.geo_type,
                    "country_code": g.country_code,
                    "parent_region": g.parent_region,
                }
                for g in extraction.geographic
            ]
            # Set top-level region for backward compat with /signals/regions endpoint
            for g in extraction.geographic:
                if g.geo_type == "state" and g.country_code == "NGA":
                    data["state"] = g.name
                    data["region"] = g.name
                    break
                elif g.geo_type == "country":
                    data["country"] = g.name
                    data["country_code"] = g.country_code

        # Add entity extraction metadata
        if extraction.entities:
            data["extracted_entities"] = [
                {
                    "name": e.name,
                    "type": e.entity_type,
                    "confidence": e.confidence,
                }
                for e in extraction.entities
            ]

        # Track extraction provenance
        data["ner_model"] = extraction.extraction_model
        data["ner_tokens"] = extraction.tokens_used

        signal.extracted_data = data

    async def _persist_market_data(
        self,
        signal: Signal,
        extraction: ExtractionResult,
    ) -> int:
        """Persist extracted numeric data as MarketDataPoint rows (returns count)."""
        mdp_list = await self._persist_market_data_with_list(signal, extraction)
        return len(mdp_list)

    async def _persist_market_data_with_list(
        self,
        signal: Signal,
        extraction: ExtractionResult,
    ) -> list[MarketDataPoint]:
        """Persist extracted numeric data as MarketDataPoint rows.

        Returns list of created MarketDataPoint objects (for change detection).
        """
        from datetime import datetime, timezone

        created_mdps: list[MarketDataPoint] = []
        # Resolve country_code from extraction or signal metadata
        country_code = None
        if extraction.geographic:
            for g in extraction.geographic:
                if g.country_code:
                    country_code = g.country_code
                    break
        if not country_code and signal.extracted_data:
            country_code = signal.extracted_data.get("country_code")

        # Resolve region from geographic extraction
        region = None
        if extraction.geographic:
            for g in extraction.geographic:
                if g.geo_type in ("state", "market", "city"):
                    region = g.name
                    break

        for ndp in extraction.numeric_data:
            try:
                mdp = MarketDataPoint(
                    metric=self._normalize_metric(ndp.metric),
                    value=ndp.value,
                    unit=ndp.unit,
                    currency=ndp.currency,
                    observed_at=signal.fetched_at or datetime.now(timezone.utc),
                    signal_id=signal.id,
                    entity_id=None,
                    country_code=country_code,
                    region=region,
                    context=ndp.context[:500] if ndp.context else None,
                    confidence=0.8,
                    metadata_=None,
                )
                self.db.add(mdp)
                created_mdps.append(mdp)
            except Exception as e:
                logger.debug(f"Failed to create MarketDataPoint for {ndp.metric}: {e}")

        if created_mdps:
            await self.db.flush()
            logger.info(
                f"Signal {signal.id}: created {len(created_mdps)} MarketDataPoint rows"
            )
        return created_mdps

    async def _run_change_detection(
        self, market_data_points: list[MarketDataPoint]
    ) -> int:
        """Run change detection on newly persisted MarketDataPoint rows.

        Returns number of alerts created.
        """
        from backend.services.change_detection import ChangeDetectionService

        detector = ChangeDetectionService(self.db)
        alerts_created = 0
        for mdp in market_data_points:
            try:
                alert = await detector.detect(mdp)
                if alert:
                    alerts_created += 1
            except Exception as e:
                logger.debug(f"Change detection failed for metric={mdp.metric}: {e}")
        return alerts_created

    @staticmethod
    def _normalize_metric(raw: str) -> str:
        """Normalize a raw metric name into a snake_case key.

        e.g. "rice price per bag" → "rice_price_per_bag"
             "NGN/USD parallel rate" → "ngn_usd_parallel_rate"
        """
        import re

        metric = raw.lower().strip()
        metric = re.sub(r"[^a-z0-9]+", "_", metric)
        metric = metric.strip("_")
        return metric[:200]  # Respect column length

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
