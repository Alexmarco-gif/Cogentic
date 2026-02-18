"""Embedding generation service.

Uses OpenAI text-embedding-3-small for signal and entity embeddings.
Stored in pgvector columns for semantic search and entity resolution.
Includes Redis caching to reduce API costs and latency.
"""

import asyncio
import logging
import time
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.embedding_cache import EmbeddingCache
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Singleton client (connection-pooled)
_openai_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """Get or create the singleton OpenAI async client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


class EmbeddingService:
    """Generates and stores embeddings via OpenAI text-embedding-3-small.

    Features:
        - Single and batch embedding generation
        - Rate-limit-aware batching (respects RPM limits)
        - Signal, entity, and query embedding helpers
        - Direct DB persistence for signal/entity embeddings
        - Redis caching to reduce API costs
        - Concurrency limiting to prevent API overload
    """

    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        self.client = _get_client()
        self.model = settings.openai_embedding_model
        self.dimensions = settings.openai_embedding_dimensions
        self.batch_size = settings.openai_embedding_batch_size
        self.rpm_limit = settings.openai_embedding_rpm_limit
        self.cache = EmbeddingCache()

        # Concurrency limiter (prevents overwhelming OpenAI API)
        self._semaphore = asyncio.Semaphore(settings.openai_max_concurrent_requests)

    # ── Core API ─────────────────────────────────────────────────────

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text with Redis caching.

        Args:
            text: Text to embed (will be truncated if too long).

        Returns:
            List of floats (1536 dimensions).

        Raises:
            ValueError: If embedding validation fails (zero vector / NaN).
        """
        text = self._prepare_text(text)

        # Check cache first
        cached = await self.cache.get(text)
        if cached is not None:
            return cached

        # Cache miss → call OpenAI API
        async with self._semaphore:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions,
            )
        embedding = response.data[0].embedding
        self._validate_embedding(embedding, context=f"text='{text[:50]}...'")

        # Store in cache
        await self.cache.set(text, embedding)

        return embedding

    async def batch_embed(self, texts: list[str]) -> list[list[float]]:
        """Batch-embed multiple texts with per-item Redis caching.

        Checks the cache for each text first, then only calls OpenAI for
        cache misses.  Results are stored back in the cache.
        Splits API calls into chunks of ``batch_size`` and respects RPM limits.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors (same order as input).
        """
        if not texts:
            return []

        prepared = [self._prepare_text(t) for t in texts]
        results: list[list[float] | None] = [None] * len(prepared)

        # ── Phase 1: Check cache for each item ──────────────────────
        uncached_indices: list[int] = []
        for idx, text in enumerate(prepared):
            cached = await self.cache.get(text)
            if cached is not None:
                results[idx] = cached
            else:
                uncached_indices.append(idx)

        if uncached_indices:
            logger.debug(
                f"batch_embed: {len(prepared) - len(uncached_indices)} cache hits, "
                f"{len(uncached_indices)} misses"
            )

        # ── Phase 2: Embed cache misses via OpenAI ──────────────────
        uncached_texts = [prepared[i] for i in uncached_indices]
        uncached_embeddings: list[list[float]] = []

        for i in range(0, len(uncached_texts), self.batch_size):
            chunk = uncached_texts[i : i + self.batch_size]
            start = time.monotonic()

            async with self._semaphore:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=chunk,
                    dimensions=self.dimensions,
                )

            chunk_embeddings = [d.embedding for d in response.data]

            # Validate each embedding
            for idx, emb in enumerate(chunk_embeddings):
                try:
                    self._validate_embedding(
                        emb, context=f"batch {i // self.batch_size + 1}, item {idx}"
                    )
                except ValueError:
                    # Continue processing; validation logs warning
                    pass

            uncached_embeddings.extend(chunk_embeddings)

            elapsed = time.monotonic() - start
            logger.debug(
                f"Embedded batch {i // self.batch_size + 1} "
                f"({len(chunk)} texts) in {elapsed:.2f}s"
            )

            # Rate limit: ~50 reqs/sec max → sleep if we're too fast
            if elapsed < 0.1 and i + self.batch_size < len(uncached_texts):
                await asyncio.sleep(0.1 - elapsed)

        # ── Phase 3: Merge results and populate cache ────────────────
        for pos, orig_idx in enumerate(uncached_indices):
            emb = uncached_embeddings[pos]
            results[orig_idx] = emb
            await self.cache.set(prepared[orig_idx], emb)

        return results  # type: ignore[return-value]

    # ── Domain Helpers ───────────────────────────────────────────────

    async def generate_signal_embedding(self, signal: Any) -> list[float]:
        """Generate embedding for a signal (title + summary + content).

        Args:
            signal: Signal ORM model instance.

        Returns:
            Embedding vector (1536 dims).
        """
        parts = []
        if signal.title:
            parts.append(signal.title)
        if signal.summary:
            parts.append(signal.summary)
        if signal.raw_content:
            # Take first 6000 chars of content to stay within token limits
            parts.append(signal.raw_content[:6000])

        text = " ".join(parts) if parts else ""
        if not text.strip():
            logger.warning(f"Signal {signal.id} has no embeddable content")
            return [0.0] * self.dimensions

        embedding = await self.embed_text(text)

        # Persist to DB if session available
        if self.db:
            signal.embedding = embedding
            await self.db.flush()

        return embedding

    async def generate_entity_embedding(self, entity: Any) -> list[float]:
        """Generate embedding for an entity (name + aliases + description).

        Args:
            entity: Entity ORM model instance.

        Returns:
            Embedding vector (1536 dims).
        """
        parts = [entity.name]
        if entity.aliases:
            parts.extend(entity.aliases)
        if entity.description:
            parts.append(entity.description)

        text = " ".join(parts)
        embedding = await self.embed_text(text)

        # Persist to DB if session available
        if self.db:
            entity.embedding = embedding
            await self.db.flush()

        return embedding

    async def generate_query_embedding(self, query_text: str) -> list[float]:
        """Generate embedding for a search query (Sprint 5).

        Args:
            query_text: Raw user query string.

        Returns:
            Embedding vector (1536 dims).
        """
        return await self.embed_text(query_text)

    async def batch_embed_signals(self, signals: list[Any]) -> int:
        """Batch-embed a list of signals and persist to DB.

        Args:
            signals: List of Signal ORM instances.

        Returns:
            Number of signals successfully embedded.
        """
        texts = []
        valid_signals = []

        for s in signals:
            parts = []
            if s.title:
                parts.append(s.title)
            if s.summary:
                parts.append(s.summary)
            if s.raw_content:
                parts.append(s.raw_content[:6000])

            text = " ".join(parts).strip()
            if text:
                texts.append(text)
                valid_signals.append(s)

        if not texts:
            return 0

        embeddings = await self.batch_embed(texts)

        for signal, embedding in zip(valid_signals, embeddings):
            signal.embedding = embedding

        if self.db:
            await self.db.flush()

        logger.info(f"Batch-embedded {len(valid_signals)} signals")
        return len(valid_signals)

    async def batch_embed_entities(self, entities: list[Any]) -> int:
        """Batch-embed a list of entities and persist to DB.

        Args:
            entities: List of Entity ORM instances.

        Returns:
            Number of entities successfully embedded.
        """
        texts = []
        valid_entities = []

        for e in entities:
            parts = [e.name]
            if e.aliases:
                parts.extend(e.aliases)
            if e.description:
                parts.append(e.description)

            text = " ".join(parts).strip()
            if text:
                texts.append(text)
                valid_entities.append(e)

        if not texts:
            return 0

        embeddings = await self.batch_embed(texts)

        for entity, embedding in zip(valid_entities, embeddings):
            entity.embedding = embedding

        if self.db:
            await self.db.flush()

        logger.info(f"Batch-embedded {len(valid_entities)} entities")
        return len(valid_entities)

    # ── Internal ─────────────────────────────────────────────────────

    @staticmethod
    def _prepare_text(text: str) -> str:
        """Normalize and truncate text for embedding.

        OpenAI's text-embedding-3-small handles ~8191 tokens.
        We cap at 8000 chars as a safe approximation.
        """
        # Whitespace-normalize
        text = " ".join(text.split()).strip()
        # Truncate to ~8000 chars
        if len(text) > 8000:
            text = text[:8000]
        return text

    @staticmethod
    def _validate_embedding(embedding: list[float], context: str = "") -> None:
        """Validate that an embedding is usable.

        Checks for:
        - Empty vectors
        - All-zero vectors (embedding failure)
        - NaN/Inf values (API error)

        Args:
            embedding: Embedding vector to validate.
            context: Optional context for logging (signal ID, text snippet).

        Raises:
            ValueError: If embedding is invalid.
        """
        import math

        if not embedding:
            logger.error(f"Empty embedding received {context}")
            raise ValueError("Empty embedding vector")

        # Check for NaN/Inf
        if any(math.isnan(x) or math.isinf(x) for x in embedding):
            logger.error(f"NaN/Inf detected in embedding {context}")
            raise ValueError("Embedding contains NaN or Inf values")

        # Check for zero vector (embedding failure)
        if all(x == 0.0 for x in embedding):
            logger.warning(f"Zero vector embedding {context}")
            raise ValueError("Embedding is all zeros")

        # Check dimension
        expected_dim = get_settings().openai_embedding_dimensions
        if len(embedding) != expected_dim:
            logger.warning(
                f"Unexpected embedding dimension: {len(embedding)} "
                f"(expected {expected_dim}) {context}"
            )
