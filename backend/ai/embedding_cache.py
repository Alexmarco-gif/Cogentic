"""Embedding cache using Redis.

Stores OpenAI embeddings to reduce API costs and latency.
Uses content hash as key for deterministic lookups.
"""

import hashlib
import json
import logging

from redis.asyncio import Redis

from backend.config import get_settings
from backend.redis_client import get_redis

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingCache:
    """Redis-based cache for OpenAI embeddings.

    Features:
        - Hash-based key generation from text content
        - Automatic TTL management (7 days default)
        - JSON serialization/deserialization
        - Cache hit/miss logging for monitoring

    Cache Key Format:
        emb:sha256:<hash>

    Cache Value:
        JSON-encoded list of floats (embedding vector)
    """

    def __init__(self):
        self.redis: Redis | None = None
        self.enabled = settings.ml_embedding_cache_enabled
        self.ttl_seconds = settings.ml_embedding_cache_ttl_days * 86400
        self.key_prefix = "emb:sha256:"

    async def _ensure_redis(self) -> Redis:
        """Lazy-load Redis connection."""
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis

    # ── Cache Operations ─────────────────────────────────────────────

    async def get(self, text: str) -> list[float] | None:
        """Retrieve cached embedding by text content.

        Args:
            text: Original text that was embedded.

        Returns:
            Cached embedding vector, or None if cache miss.
        """
        if not self.enabled:
            return None

        redis = await self._ensure_redis()
        cache_key = self._compute_key(text)

        try:
            cached_value = await redis.get(cache_key)
            if cached_value:
                embedding = json.loads(cached_value)
                logger.debug(f"Cache HIT for key={cache_key[:40]}...")
                return embedding

            logger.debug(f"Cache MISS for key={cache_key[:40]}...")
            return None

        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None

    async def set(self, text: str, embedding: list[float]) -> None:
        """Store embedding in cache with TTL.

        Args:
            text: Original text.
            embedding: Embedding vector (1536 floats).
        """
        if not self.enabled:
            return

        redis = await self._ensure_redis()
        cache_key = self._compute_key(text)

        try:
            cached_value = json.dumps(embedding)
            await redis.setex(cache_key, self.ttl_seconds, cached_value)
            logger.debug(
                f"Cache SET for key={cache_key[:40]}... "
                f"(TTL={settings.ml_embedding_cache_ttl_days} days)"
            )

        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    async def invalidate(self, text: str) -> None:
        """Remove embedding from cache.

        Args:
            text: Original text to invalidate.
        """
        if not self.enabled:
            return

        redis = await self._ensure_redis()
        cache_key = self._compute_key(text)

        try:
            await redis.delete(cache_key)
            logger.debug(f"Cache INVALIDATE for key={cache_key[:40]}...")
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")

    # ── Internal ─────────────────────────────────────────────────────

    @staticmethod
    def _compute_key(text: str) -> str:
        """Generate cache key from text content using SHA256.

        Args:
            text: Text content to hash.

        Returns:
            Redis key in format 'emb:sha256:<hash>'
        """
        # Normalize whitespace for consistent hashing
        normalized = " ".join(text.split()).strip().lower()

        # Compute SHA256 hash
        hash_obj = hashlib.sha256(normalized.encode("utf-8"))
        hash_hex = hash_obj.hexdigest()

        return f"emb:sha256:{hash_hex}"

    async def get_stats(self) -> dict:
        """Get cache statistics (for monitoring).

        Returns:
            Dict with cache hit rate, size, etc.
        """
        if not self.enabled:
            return {"enabled": False}

        redis = await self._ensure_redis()

        try:
            # Count cache keys
            cursor = 0
            key_count = 0
            pattern = f"{self.key_prefix}*"

            while True:
                cursor, keys = await redis.scan(cursor, match=pattern, count=100)
                key_count += len(keys)
                if cursor == 0:
                    break

            # Get memory usage (if available)
            info = await redis.info("memory")
            memory_used = info.get("used_memory_human", "N/A")

            return {
                "enabled": True,
                "key_count": key_count,
                "memory_used": memory_used,
                "ttl_days": settings.ml_embedding_cache_ttl_days,
            }

        except Exception as e:
            logger.warning(f"Cache stats error: {e}")
            return {"enabled": True, "error": str(e)}
