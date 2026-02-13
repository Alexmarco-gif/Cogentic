"""Deep Live Search service.

Search orchestrator: parse intent → expand query → parallel fetch → rank → synthesize.
Targets P95 < 5 seconds.
Persists to SearchQuery model with timing and results.
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.embeddings import EmbeddingService
from backend.ai.guardrails import get_guardrails
from backend.ai.synthesis import SynthesisService
from backend.config import get_settings
from backend.database import get_db_context
from backend.models.search_query import SearchQuery
from backend.redis_client import get_redis

logger = logging.getLogger(__name__)
settings = get_settings()

# Search config
SEARCH_CACHE_TTL = 900  # 15 minutes
SEARCH_MAX_RESULTS = 20
SEARCH_TIMEOUT_MS = 5000  # P95 target


class DeepSearchService:
    """Deep Live Search engine.

    Pipeline:
      1. Parse intent & sanitize query
      2. Generate query embedding
      3. Expand query using entity embeddings
      4. Parallel fetch: pgvector signals + entity matches
      5. Semantic ranking via embedding similarity + confidence + freshness
      6. Result dedup and fusion
      7. Optional AI synthesis of top results
      8. Persist to SearchQuery model

    Target: P95 < 5 seconds.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService(db)
        self.synthesis = SynthesisService(db)
        self.guardrails = get_guardrails()

    async def search(
        self,
        query: str,
        *,
        user_id: UUID,
        org_id: UUID,
        industry_id: UUID | None = None,
        synthesize: bool = True,
        max_results: int = SEARCH_MAX_RESULTS,
    ) -> dict[str, Any]:
        """Execute deep search pipeline.

        Args:
            query: User search query.
            user_id: Requesting user.
            org_id: Tenant scope.
            industry_id: Optional industry filter.
            synthesize: Whether to run AI synthesis on results.
            max_results: Max signals to return.

        Returns:
            Search result dict with signals, synthesis, timing.
        """
        start = time.monotonic()

        # Step 1: Sanitize input
        sanitized = self.guardrails.sanitize_input(query, context="search")
        if not sanitized.is_safe and sanitized.injection_detected:
            return self._error_result(
                "Query flagged for safety review. Please rephrase.", query, start
            )
        clean_query = sanitized.text

        # Step 2: Check cache
        query_hash = self._hash_query(clean_query, org_id)
        cached = await self._get_cached(query_hash)
        if cached:
            cached["cached"] = True
            cached["response_time_ms"] = int((time.monotonic() - start) * 1000)
            return cached

        # Step 3: Generate query embedding
        try:
            query_embedding = await self.embedding_service.generate_query_embedding(
                clean_query
            )
        except Exception as e:
            logger.error(f"Query embedding failed: {e}")
            return self._error_result("Search temporarily unavailable.", query, start)

        # Step 4: Parallel fetch — signals + entities
        signal_task = self._search_signals(
            query_embedding,
            org_id=org_id,
            industry_id=industry_id,
            limit=max_results,
        )
        entity_task = self._search_entities(
            query_embedding,
            limit=10,
        )

        signals, entities = await asyncio.gather(
            signal_task, entity_task, return_exceptions=True
        )

        if isinstance(signals, Exception):
            logger.error(f"Signal search failed: {signals}")
            signals = []
        if isinstance(entities, Exception):
            logger.error(f"Entity search failed: {entities}")
            entities = []

        # Step 5: Rank and deduplicate
        ranked_signals = self._rank_results(signals)

        # Step 6: Optional AI synthesis
        synthesis_result = None
        if synthesize and ranked_signals:
            try:
                synthesis_result = await self.synthesis.synthesize(
                    clean_query,
                    org_id=org_id,
                    industry_id=industry_id,
                    top_k=min(10, len(ranked_signals)),
                )
            except Exception as e:
                logger.error(f"Synthesis during search failed: {e}")

        response_time_ms = int((time.monotonic() - start) * 1000)

        result = {
            "query": clean_query,
            "query_hash": query_hash,
            "signals": ranked_signals[:max_results],
            "entities": entities[:10],
            "synthesis": synthesis_result.get("answer") if synthesis_result else None,
            "source_count": len(ranked_signals),
            "entity_count": len(entities),
            "cached": False,
            "response_time_ms": response_time_ms,
        }

        # Step 7: Persist to SearchQuery model
        await self._persist_result(
            user_id=user_id,
            org_id=org_id,
            query_text=clean_query,
            query_hash=query_hash,
            result=result,
            response_time_ms=response_time_ms,
        )

        # Step 8: Cache result
        await self._set_cached(query_hash, result)

        return result

    async def get_search_history(
        self,
        user_id: UUID,
        org_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get user's search history."""
        from backend.repositories.search_query import SearchQueryRepository

        repo = SearchQueryRepository(self.db, org_id, user_id)
        queries = await repo.get_user_history(user_id, skip=skip, limit=limit)
        return [
            {
                "id": str(q.id),
                "query_text": q.query_text,
                "source_count": q.source_count,
                "response_time_ms": q.response_time_ms,
                "created_at": q.created_at.isoformat(),
            }
            for q in queries
        ]

    # ── Signal Search ────────────────────────────────────────────────

    async def _search_signals(
        self,
        query_embedding: list[float],
        *,
        org_id: UUID | None = None,
        industry_id: UUID | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search signals via pgvector cosine similarity."""
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        conditions = [
            "s.embedding IS NOT NULL",
            "s.confidence >= 0.50",
        ]
        if org_id:
            conditions.append(f"(s.org_id IS NULL OR s.org_id = '{org_id}')")
        if industry_id:
            conditions.append(
                f"s.contract_id IN (SELECT id FROM signal_contracts WHERE industry_id = '{industry_id}')"
            )

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT
                s.id, s.title, s.summary, s.confidence,
                s.signal_type, s.source_url, s.published_at,
                s.created_at,
                s.embedding <=> :embedding AS distance
            FROM signals s
            WHERE {where_clause}
            ORDER BY s.embedding <=> :embedding
            LIMIT :limit
        """
        )

        result = await self.db.execute(
            query, {"embedding": embedding_str, "limit": limit}
        )
        rows = result.fetchall()

        return [
            {
                "id": str(r.id),
                "title": r.title or "Untitled Signal",
                "summary": r.summary or "",
                "confidence": float(r.confidence),
                "signal_type": r.signal_type,
                "source_url": r.source_url,
                "published_at": r.published_at.isoformat() if r.published_at else None,
                "similarity": round(1.0 - (r.distance or 1.0), 4),
                "freshness_score": self._calc_freshness(r.published_at or r.created_at),
            }
            for r in rows
        ]

    async def _search_entities(
        self,
        query_embedding: list[float],
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search entities via pgvector cosine similarity."""
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        query = text(
            """
            SELECT
                e.id, e.name, e.entity_type, e.description,
                e.embedding <=> :embedding AS distance
            FROM entities e
            WHERE e.embedding IS NOT NULL
            ORDER BY e.embedding <=> :embedding
            LIMIT :limit
        """
        )

        result = await self.db.execute(
            query, {"embedding": embedding_str, "limit": limit}
        )
        rows = result.fetchall()

        return [
            {
                "id": str(r.id),
                "name": r.name,
                "entity_type": r.entity_type,
                "description": r.description or "",
                "similarity": round(1.0 - (r.distance or 1.0), 4),
            }
            for r in rows
        ]

    # ── Ranking ──────────────────────────────────────────────────────

    def _rank_results(self, signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank signals by composite score: similarity + confidence + freshness.

        Weights:
          - Similarity: 0.50 (embedding relevance)
          - Confidence: 0.30 (signal quality)
          - Freshness: 0.20 (recency)
        """
        for sig in signals:
            composite = (
                sig.get("similarity", 0) * 0.50
                + sig.get("confidence", 0) * 0.30
                + sig.get("freshness_score", 0) * 0.20
            )
            sig["rank_score"] = round(composite, 4)

        # Sort by composite rank descending
        signals.sort(key=lambda s: s.get("rank_score", 0), reverse=True)

        # Dedup by title (keep highest-ranked)
        seen_titles = set()
        deduped = []
        for sig in signals:
            title_key = (sig.get("title") or "").lower().strip()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                deduped.append(sig)

        return deduped

    @staticmethod
    def _calc_freshness(dt: Any) -> float:
        """Calculate freshness score (0.0 to 1.0) based on age.

        - < 1 day: 1.0
        - 1-7 days: 0.8
        - 7-30 days: 0.6
        - 30-90 days: 0.4
        - > 90 days: 0.2
        """
        if not dt:
            return 0.3

        from datetime import timezone

        if hasattr(dt, "tzinfo") and dt.tzinfo:
            now = datetime.now(timezone.utc)
        else:
            now = datetime.utcnow()

        age_days = (now - dt).days
        if age_days < 1:
            return 1.0
        elif age_days < 7:
            return 0.8
        elif age_days < 30:
            return 0.6
        elif age_days < 90:
            return 0.4
        return 0.2

    # ── Persistence ──────────────────────────────────────────────────

    async def _persist_result(
        self,
        *,
        user_id: UUID,
        org_id: UUID,
        query_text: str,
        query_hash: str,
        result: dict[str, Any],
        response_time_ms: int,
    ) -> None:
        """Persist search query and results to DB."""
        try:
            search_query = SearchQuery(
                user_id=user_id,
                org_id=org_id,
                query_text=query_text,
                query_hash=query_hash,
                results_json={
                    "signals": [s["id"] for s in result.get("signals", [])[:20]],
                    "entity_count": result.get("entity_count", 0),
                    "has_synthesis": result.get("synthesis") is not None,
                },
                source_count=result.get("source_count", 0),
                response_time_ms=response_time_ms,
            )
            self.db.add(search_query)
            await self.db.flush()
        except Exception as e:
            logger.error(f"Failed to persist search query: {e}")

    # ── Caching ──────────────────────────────────────────────────────

    @staticmethod
    def _hash_query(query: str, org_id: UUID | None = None) -> str:
        key_parts = [query.lower().strip()]
        if org_id:
            key_parts.append(str(org_id))
        return hashlib.sha256("|".join(key_parts).encode()).hexdigest()

    async def _get_cached(self, query_hash: str) -> dict[str, Any] | None:
        try:
            redis = await get_redis()
            data = await redis.get(f"search:{query_hash}")
            if data:
                logger.debug(f"Search cache hit: {query_hash[:16]}...")
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Search cache read failed: {e}")
        return None

    async def _set_cached(self, query_hash: str, result: dict[str, Any]) -> None:
        try:
            redis = await get_redis()
            if result.get("source_count", 0) > 0:
                await redis.setex(
                    f"search:{query_hash}",
                    SEARCH_CACHE_TTL,
                    json.dumps(result, default=str),
                )
        except Exception as e:
            logger.warning(f"Search cache write failed: {e}")

    @staticmethod
    def _error_result(message: str, query: str, start: float) -> dict[str, Any]:
        return {
            "query": query,
            "query_hash": "",
            "signals": [],
            "entities": [],
            "synthesis": None,
            "source_count": 0,
            "entity_count": 0,
            "cached": False,
            "response_time_ms": int((time.monotonic() - start) * 1000),
            "error": message,
        }


# ── Synchronous wrappers for RQ workers ──────────────────────────────


def run_deep_search(
    query: str,
    user_id: str,
    org_id: str,
    industry_id: str | None = None,
) -> dict[str, Any]:
    """Sync wrapper for RQ: execute deep search."""

    async def _run():
        async with get_db_context() as db:
            service = DeepSearchService(db)
            return await service.search(
                query,
                user_id=UUID(user_id),
                org_id=UUID(org_id),
                industry_id=UUID(industry_id) if industry_id else None,
            )

    return asyncio.run(_run())
