"""Recommendation engine.

Generates recommendations using embedding similarity + entity overlap + industry alignment.
Persists to Recommendation model with score, reason, algorithm_version.
Runs as batch RQ job after refinement.
"""

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_db_context
from backend.models.recommendation import Recommendation
from backend.models.signal import Signal

logger = logging.getLogger(__name__)
settings = get_settings()

ALGORITHM_VERSION = "v1.0-embedding-entity"
MIN_RECOMMENDATION_SCORE = 0.40
MAX_RECOMMENDATIONS_PER_SOURCE = 5


class RecommendationService:
    """Generates "Related signals" and "You might also need" recommendations.

    Algorithm:
      1. Embedding similarity (pgvector cosine distance) → 60% weight
      2. Entity overlap (shared entity links) → 25% weight
      3. Industry alignment (same industry) → 15% weight

    Stores to Recommendation model with score + reason.
    Runs as batch job after refinement pipeline.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_for_signal(
        self,
        signal_id: UUID,
        *,
        max_recs: int = MAX_RECOMMENDATIONS_PER_SOURCE,
        min_score: float = MIN_RECOMMENDATION_SCORE,
    ) -> list[dict[str, Any]]:
        """Generate recommendations for a single signal.

        Args:
            signal_id: Source signal ID.
            max_recs: Maximum recommendations to generate.
            min_score: Minimum score threshold.

        Returns:
            List of recommendation dicts.
        """
        # Get source signal with embedding
        result = await self.db.execute(
            select(Signal).where(Signal.id == signal_id)
        )
        source = result.scalar_one_or_none()

        if not source or source.embedding is None:
            logger.warning(f"Signal {signal_id} not found or has no embedding")
            return []

        # Step 1: Embedding similarity search (exclude self)
        similar_signals = await self._find_similar_signals(
            signal_id, source.embedding, limit=max_recs * 2
        )

        # Step 2: Entity overlap scoring
        source_entities = await self._get_signal_entities(signal_id)

        # Step 3: Industry alignment
        source_industry_id = await self._get_signal_industry(signal_id)

        # Score candidates
        recommendations = []
        for candidate in similar_signals:
            if candidate["id"] == str(signal_id):
                continue

            cand_id = UUID(candidate["id"])
            cand_entities = await self._get_signal_entities(cand_id)
            cand_industry_id = await self._get_signal_industry(cand_id)

            # Composite score
            sim_score = candidate["similarity"]
            entity_overlap = self._calc_entity_overlap(source_entities, cand_entities)
            industry_match = 1.0 if (
                source_industry_id and cand_industry_id
                and source_industry_id == cand_industry_id
            ) else 0.0

            composite = (
                sim_score * 0.60
                + entity_overlap * 0.25
                + industry_match * 0.15
            )

            if composite < min_score:
                continue

            # Build reason string
            reason_parts = []
            if sim_score > 0.7:
                reason_parts.append(f"High content similarity ({sim_score:.0%})")
            if entity_overlap > 0:
                reason_parts.append(f"Shared entities ({entity_overlap:.0%} overlap)")
            if industry_match > 0:
                reason_parts.append("Same industry")
            reason = ". ".join(reason_parts) if reason_parts else "Related content"

            recommendations.append({
                "source_type": "signal",
                "source_id": str(signal_id),
                "target_type": "signal",
                "target_id": candidate["id"],
                "score": round(composite, 4),
                "reason": reason,
                "algorithm_version": ALGORITHM_VERSION,
            })

        # Sort by score and take top max_recs
        recommendations.sort(key=lambda r: r["score"], reverse=True)
        recommendations = recommendations[:max_recs]

        # Persist to DB
        await self._persist_recommendations(recommendations)

        return recommendations

    async def generate_batch(
        self,
        *,
        limit: int = 100,
        min_confidence: float = 0.60,
    ) -> dict[str, Any]:
        """Generate recommendations for a batch of signals.

        Called after refinement pipeline completes.

        Args:
            limit: Max signals to process.
            min_confidence: Only recommend high-confidence signals.

        Returns:
            Batch summary dict.
        """
        start = time.monotonic()

        # Find signals with embeddings that need recommendations
        result = await self.db.execute(
            select(Signal.id).where(
                Signal.embedding.isnot(None),
                Signal.confidence >= min_confidence,
            )
            .order_by(Signal.created_at.desc())
            .limit(limit)
        )
        signal_ids = [row[0] for row in result.all()]

        if not signal_ids:
            return {"processed": 0, "recommendations": 0, "errors": 0}

        total_recs = 0
        errors = 0

        for sid in signal_ids:
            try:
                recs = await self.generate_for_signal(sid)
                total_recs += len(recs)
            except Exception as e:
                errors += 1
                logger.error(f"Recommendation generation failed for {sid}: {e}")

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            f"Batch recommendations: {len(signal_ids)} signals, "
            f"{total_recs} recs, {errors} errors, {duration_ms}ms"
        )

        return {
            "processed": len(signal_ids),
            "recommendations": total_recs,
            "errors": errors,
            "duration_ms": duration_ms,
        }

    async def get_for_signal(
        self,
        signal_id: UUID,
        *,
        limit: int = 10,
    ) -> list[Recommendation]:
        """Get existing recommendations for a signal."""
        result = await self.db.execute(
            select(Recommendation).where(
                Recommendation.source_type == "signal",
                Recommendation.source_id == signal_id,
            )
            .order_by(Recommendation.score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_active(
        self,
        *,
        source_type: str = "signal",
        limit: int = 50,
        min_score: float = 0.50,
    ) -> list[Recommendation]:
        """Get active high-scoring recommendations."""
        result = await self.db.execute(
            select(Recommendation).where(
                Recommendation.source_type == source_type,
                Recommendation.score >= min_score,
            )
            .order_by(Recommendation.score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── Internal Helpers ─────────────────────────────────────────────

    async def _find_similar_signals(
        self,
        exclude_id: UUID,
        embedding: Any,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Find similar signals via pgvector, excluding source."""
        embedding_list = list(embedding) if not isinstance(embedding, list) else embedding
        embedding_str = "[" + ",".join(str(v) for v in embedding_list) + "]"

        query = text("""
            SELECT
                s.id, s.title, s.confidence,
                s.embedding <=> :embedding AS distance
            FROM signals s
            WHERE s.embedding IS NOT NULL
              AND s.id != :exclude_id
              AND s.confidence >= 0.50
            ORDER BY s.embedding <=> :embedding
            LIMIT :limit
        """)

        result = await self.db.execute(
            query,
            {
                "embedding": embedding_str,
                "exclude_id": exclude_id,
                "limit": limit,
            },
        )
        rows = result.fetchall()

        return [
            {
                "id": str(r.id),
                "title": r.title or "Untitled",
                "confidence": float(r.confidence),
                "similarity": round(1.0 - (r.distance or 1.0), 4),
            }
            for r in rows
        ]

    async def _get_signal_entities(self, signal_id: UUID) -> set[UUID]:
        """Get entity IDs linked to a signal."""
        result = await self.db.execute(
            text(
                "SELECT entity_id FROM signal_entities WHERE signal_id = :sid"
            ),
            {"sid": signal_id},
        )
        return {row[0] for row in result.all()}

    async def _get_signal_industry(self, signal_id: UUID) -> UUID | None:
        """Get industry_id for a signal via its contract."""
        result = await self.db.execute(
            text("""
                SELECT sc.industry_id
                FROM signals s
                JOIN signal_contracts sc ON s.contract_id = sc.id
                WHERE s.id = :sid
            """),
            {"sid": signal_id},
        )
        row = result.first()
        return row[0] if row else None

    @staticmethod
    def _calc_entity_overlap(entities_a: set[UUID], entities_b: set[UUID]) -> float:
        """Calculate Jaccard overlap between two entity sets."""
        if not entities_a or not entities_b:
            return 0.0
        intersection = entities_a & entities_b
        union = entities_a | entities_b
        return len(intersection) / len(union) if union else 0.0

    async def _persist_recommendations(
        self, recommendations: list[dict[str, Any]]
    ) -> None:
        """Persist recommendation records to DB."""
        for rec in recommendations:
            # Upsert: delete existing rec for same source→target, then create
            existing = await self.db.execute(
                select(Recommendation).where(
                    Recommendation.source_type == rec["source_type"],
                    Recommendation.source_id == UUID(rec["source_id"]),
                    Recommendation.target_type == rec["target_type"],
                    Recommendation.target_id == UUID(rec["target_id"]),
                )
            )
            old = existing.scalar_one_or_none()
            if old:
                old.score = rec["score"]
                old.reason = rec["reason"]
                old.algorithm_version = rec["algorithm_version"]
            else:
                self.db.add(Recommendation(
                    source_type=rec["source_type"],
                    source_id=UUID(rec["source_id"]),
                    target_type=rec["target_type"],
                    target_id=UUID(rec["target_id"]),
                    score=rec["score"],
                    reason=rec["reason"],
                    algorithm_version=rec["algorithm_version"],
                ))
        await self.db.flush()


# ── Synchronous wrappers for RQ workers ──────────────────────────────


def run_recommendation_batch(
    limit: int = 100,
    min_confidence: float = 0.60,
) -> dict[str, Any]:
    """Sync wrapper for RQ: generate batch recommendations."""

    async def _run():
        async with get_db_context() as db:
            service = RecommendationService(db)
            return await service.generate_batch(
                limit=limit,
                min_confidence=min_confidence,
            )

    return asyncio.run(_run())
