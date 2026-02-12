"""Signal deduplication processor.

Two-layer dedup:
1. Exact match: SHA-256 content hash (Sprint 2)
2. Semantic similarity: cosine similarity > 0.95 via pgvector embeddings (Sprint 3)
"""

import hashlib
import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.signal import Signal
from backend.signals.fetchers.base import FetchResult

logger = logging.getLogger(__name__)
settings = get_settings()


class DedupProcessor:
    """Deduplicates signals using content hashing + semantic similarity.

    Layer 1: SHA-256 exact content hash (fast, deterministic).
    Layer 2: Cosine similarity > threshold via pgvector embeddings (semantic).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.semantic_threshold = settings.ml_semantic_dedup_threshold

    async def is_duplicate(self, result: FetchResult) -> bool:
        """Check if a FetchResult is a duplicate of an existing signal.

        Args:
            result: The fetched result to check.

        Returns:
            True if duplicate, False if new.
        """
        if not result.content_hash:
            result.content_hash = self._compute_hash(result.content)

        existing = await self.db.execute(
            select(Signal.id).where(Signal.content_hash == result.content_hash).limit(1)
        )
        return existing.scalar_one_or_none() is not None

    async def is_semantic_duplicate(
        self,
        embedding: list[float],
    ) -> bool:
        """Check if a signal embedding is semantically duplicate (Layer 2).

        Uses pgvector cosine distance (<=>). Only runs if signal has an embedding.

        Args:
            embedding: The signal's embedding vector (1536 dims).

        Returns:
            True if a near-duplicate exists (similarity > threshold).
        """
        if not embedding:
            return False

        query = text("""
            SELECT id, 1 - (embedding <=> :embedding) AS similarity
            FROM signals
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :embedding
            LIMIT 1
        """)

        result = await self.db.execute(
            query, {"embedding": str(embedding)}
        )
        row = result.first()

        if row and row.similarity >= self.semantic_threshold:
            logger.info(
                f"Semantic duplicate detected: similarity={row.similarity:.4f} "
                f"(threshold={self.semantic_threshold}) existing_id={row.id}"
            )
            return True

        return False

    async def filter_duplicates(
        self,
        results: list[FetchResult],
    ) -> list[FetchResult]:
        """Filter out duplicate results, keeping only new ones.

        Checks both against existing DB signals and within the batch itself.

        Args:
            results: List of fetched results to filter.

        Returns:
            List of non-duplicate results.
        """
        if not results:
            return []

        # Compute hashes for all results
        for r in results:
            if not r.content_hash:
                r.content_hash = self._compute_hash(r.content)

        # Batch-check existing hashes against DB
        hashes = [r.content_hash for r in results if r.content_hash]
        if not hashes:
            return results

        existing_result = await self.db.execute(
            select(Signal.content_hash).where(Signal.content_hash.in_(hashes))
        )
        existing_hashes: set[str] = {row[0] for row in existing_result.all()}

        # Also deduplicate within the batch
        seen: set[str] = set()
        unique: list[FetchResult] = []

        for r in results:
            h = r.content_hash
            if h and h not in existing_hashes and h not in seen:
                seen.add(h)
                unique.append(r)

        dupes_found = len(results) - len(unique)
        if dupes_found > 0:
            logger.info(
                f"Dedup: filtered {dupes_found} duplicates, {len(unique)} new signals"
            )

        return unique

    @staticmethod
    def _compute_hash(content: str) -> str:
        """SHA-256 hash of content for dedup (whitespace-normalized)."""
        normalized = " ".join(content.split()).strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
