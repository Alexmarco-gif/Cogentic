"""Entity resolution engine.

Matches incoming signal content to existing entities using:
1. Embedding cosine similarity (pgvector <=> operator) — primary
2. Fuzzy string matching on entity names/aliases — fallback

Creates SignalEntity junction records with relevance_score.
Target: >90% accuracy on entity-signal linking.
"""

import logging
import re
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.embeddings import EmbeddingService
from backend.config import get_settings
from backend.models.entity import Entity
from backend.models.signal import Signal
from backend.models.signal_entity import SignalEntity

logger = logging.getLogger(__name__)
settings = get_settings()


class EntityResolver:
    """Resolves entities mentioned in signals.

    Resolution strategy (ordered):
      1. Semantic: cosine similarity of signal ↔ entity embeddings via pgvector
      2. Fuzzy: case-insensitive substring/alias matching on signal text

    Deduplicates matches (same signal+entity pair) via upsert logic.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService(db)
        self.similarity_threshold = settings.ml_entity_similarity_threshold

    async def resolve_signal(self, signal: Signal) -> list[SignalEntity]:
        """Resolve all entities for a given signal.

        Combines semantic + fuzzy matches, deduplicates, and persists.

        Args:
            signal: Signal ORM instance (must have embedding set).

        Returns:
            List of created/updated SignalEntity junction records.
        """
        matches: dict[UUID, float] = {}  # entity_id → best relevance_score

        # Layer 1: Semantic matching via pgvector
        if signal.embedding is not None:
            semantic_matches = await self._semantic_match(signal)
            for entity_id, score in semantic_matches:
                if entity_id not in matches or score > matches[entity_id]:
                    matches[entity_id] = score

        # Layer 2: Fuzzy string matching
        signal_text = self._build_signal_text(signal)
        if signal_text:
            fuzzy_matches = await self._fuzzy_match(signal_text)
            for entity_id, score in fuzzy_matches:
                if entity_id not in matches or score > matches[entity_id]:
                    matches[entity_id] = score

        if not matches:
            logger.debug(f"No entity matches for signal {signal.id}")
            return []

        # Filter by minimum confidence threshold
        min_confidence = settings.ml_entity_min_confidence
        filtered_matches = {
            entity_id: score
            for entity_id, score in matches.items()
            if score >= min_confidence
        }

        if not filtered_matches:
            logger.debug(
                f"No entity matches above confidence threshold "
                f"({min_confidence}) for signal {signal.id}"
            )
            return []

        # Persist SignalEntity records (upsert)
        results = []
        for entity_id, relevance_score in filtered_matches.items():
            link = await self._upsert_link(signal.id, entity_id, relevance_score)
            results.append(link)

        logger.info(
            f"Resolved {len(results)} entities for signal {signal.id} "
            f"(total matches={len(matches)}, "
            f"above threshold={len(filtered_matches)}, "
            f"min_confidence={min_confidence})"
        )
        return results

    async def resolve_batch(self, signals: list[Signal]) -> int:
        """Resolve entities for a batch of signals.

        Args:
            signals: List of Signal ORM instances.

        Returns:
            Total number of entity links created.
        """
        total_links = 0
        for signal in signals:
            try:
                links = await self.resolve_signal(signal)
                total_links += len(links)
            except Exception as e:
                logger.error(f"Entity resolution failed for signal {signal.id}: {e}")
        return total_links

    # ── Semantic Matching ────────────────────────────────────────────

    async def _semantic_match(
        self,
        signal: Signal,
        *,
        top_k: int = 10,
    ) -> list[tuple[UUID, float]]:
        """Find entities semantically similar to this signal via pgvector.

        Uses cosine distance operator (<=>). Lower distance = more similar.
        Converts distance → similarity: sim = 1 - distance.

        Returns:
            List of (entity_id, similarity_score) tuples above threshold.
        """
        # pgvector cosine distance: <=> returns 0..2 (0 = identical)
        query = text("""
            SELECT id, 1 - (embedding <=> :embedding) AS similarity
            FROM entities
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :embedding
            LIMIT :top_k
        """)

        result = await self.db.execute(
            query,
            {
                "embedding": str(signal.embedding),
                "top_k": top_k,
            },
        )

        matches = []
        for row in result.all():
            entity_id, similarity = row
            if similarity >= self.similarity_threshold:
                matches.append((entity_id, round(float(similarity), 4)))

        return matches

    # ── Fuzzy String Matching ────────────────────────────────────────

    async def _fuzzy_match(
        self,
        signal_text: str,
    ) -> list[tuple[UUID, float]]:
        """Match entities by name/alias substring in signal text.

        Case-insensitive. Scores based on match quality:
        - Exact name match: 0.9
        - Alias match: 0.8
        - Partial name match (word boundary): 0.7

        Returns:
            List of (entity_id, relevance_score) tuples.
        """
        # Load all entities (cached in practice; small table)
        from sqlalchemy import select

        result = await self.db.execute(
            select(Entity.id, Entity.name, Entity.aliases)
        )

        signal_lower = signal_text.lower()
        matches = []

        for entity_id, name, aliases in result.all():
            best_score = 0.0
            name_lower = name.lower()

            # Exact name match
            if name_lower in signal_lower:
                # Check word boundary for precision
                pattern = r'\b' + re.escape(name_lower) + r'\b'
                if re.search(pattern, signal_lower):
                    best_score = 0.9
                else:
                    best_score = 0.7

            # Alias matches
            if aliases:
                for alias in aliases:
                    alias_lower = alias.lower().strip()
                    if not alias_lower or len(alias_lower) < 3:
                        continue
                    if alias_lower in signal_lower:
                        pattern = r'\b' + re.escape(alias_lower) + r'\b'
                        if re.search(pattern, signal_lower):
                            best_score = max(best_score, 0.8)
                        else:
                            best_score = max(best_score, 0.65)

            if best_score >= 0.65:
                matches.append((entity_id, best_score))

        return matches

    # ── Helpers ───────────────────────────────────────────────────────

    async def _upsert_link(
        self,
        signal_id: UUID,
        entity_id: UUID,
        relevance_score: float,
    ) -> SignalEntity:
        """Create or update a SignalEntity junction record."""
        from sqlalchemy import select

        existing = await self.db.execute(
            select(SignalEntity).where(
                SignalEntity.signal_id == signal_id,
                SignalEntity.entity_id == entity_id,
            )
        )
        link = existing.scalar_one_or_none()

        if link:
            # Update if new score is higher
            if relevance_score > link.relevance_score:
                link.relevance_score = relevance_score
                await self.db.flush()
            return link

        # Create new link
        link = SignalEntity(
            signal_id=signal_id,
            entity_id=entity_id,
            relevance_score=relevance_score,
        )
        self.db.add(link)
        await self.db.flush()
        return link

    @staticmethod
    def _build_signal_text(signal: Signal) -> str:
        """Combine signal text fields for fuzzy matching."""
        parts = []
        if signal.title:
            parts.append(signal.title)
        if signal.summary:
            parts.append(signal.summary)
        if signal.raw_content:
            parts.append(signal.raw_content[:3000])
        return " ".join(parts)
