"""Redis-backed cache for web search queries.

Caches raw SerpApi results per query+engine to reduce API costs.
Short TTL (configurable, default 15 min) since web results change frequently.

Usage:
    cache = WebSearchCache()
    cached = await cache.get("fintech Nigeria", "google")
    if cached is not None:
        return cached

    results = await provider.search("fintech Nigeria")
    await cache.set("fintech Nigeria", "google", results)
"""

import hashlib
import json
import logging
from datetime import datetime

from backend.config import get_settings
from backend.services.web_search.base import WebSearchResult

logger = logging.getLogger(__name__)
settings = get_settings()


class WebSearchCache:
    """Redis cache for web search results.

    Key format: ``websearch:{sha256(query|engine)}``
    Value: JSON-serialized list of WebSearchResult dicts.
    TTL: ``settings.web_search_cache_ttl`` seconds (default 900 = 15 min).
    """

    @staticmethod
    def _cache_key(query: str, engine: str) -> str:
        """Generate a deterministic cache key from query + engine."""
        raw = f"{query.lower().strip()}|{engine.lower().strip()}"
        h = hashlib.sha256(raw.encode()).hexdigest()
        return f"websearch:{h}"

    @staticmethod
    def _serialize(results: list[WebSearchResult]) -> str:
        """Serialize a list of WebSearchResult to JSON string."""
        return json.dumps(
            [r.to_dict() for r in results],
            default=str,
        )

    @staticmethod
    def _deserialize(data: str) -> list[WebSearchResult] | None:
        """Deserialize JSON string back to list of WebSearchResult.

        Returns None if deserialization fails (corrupt cache entry).
        """
        try:
            items = json.loads(data)
            if not isinstance(items, list):
                return None
            results = []
            for item in items:
                published_at = None
                if item.get("published_at"):
                    try:
                        published_at = datetime.fromisoformat(item["published_at"])
                    except (ValueError, TypeError):
                        pass

                results.append(
                    WebSearchResult(
                        title=item.get("title", ""),
                        snippet=item.get("snippet", ""),
                        url=item.get("url", ""),
                        source=item.get("source", ""),
                        position=item.get("position", 0),
                        published_at=published_at,
                        thumbnail_url=item.get("thumbnail_url"),
                        relevance_score=item.get("relevance_score", 0.0),
                        confidence=item.get("confidence", 0.65),
                        metadata=item.get("metadata", {}),
                    )
                )
            return results
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"Web search cache deserialization failed: {e}")
            return None

    async def get(
        self,
        query: str,
        engine: str,
    ) -> list[WebSearchResult] | None:
        """Retrieve cached web search results.

        Returns:
            List of WebSearchResult if cache hit, None on miss or error.
        """
        try:
            from backend.redis_client import get_redis

            redis = await get_redis()
            key = self._cache_key(query, engine)
            data = await redis.get(key)
            if data:
                results = self._deserialize(data)
                if results is not None:
                    logger.debug(
                        f"Web search cache hit: {key[:24]}… "
                        f"({len(results)} results)"
                    )
                    return results
        except Exception as e:
            logger.warning(f"Web search cache read failed: {e}")
        return None

    async def set(
        self,
        query: str,
        engine: str,
        results: list[WebSearchResult],
        ttl: int | None = None,
    ) -> None:
        """Cache web search results.

        Args:
            query: Original search query.
            engine: Engine name (e.g. "google", "google_news").
            results: List of WebSearchResult objects to cache.
            ttl: Cache TTL in seconds. Defaults to settings.web_search_cache_ttl.
        """
        if not results:
            return  # Don't cache empty results

        try:
            from backend.redis_client import get_redis

            redis = await get_redis()
            key = self._cache_key(query, engine)
            data = self._serialize(results)
            await redis.setex(
                key,
                ttl or settings.web_search_cache_ttl,
                data,
            )
            logger.debug(
                f"Web search cached: {key[:24]}… "
                f"({len(results)} results, TTL={ttl or settings.web_search_cache_ttl}s)"
            )
        except Exception as e:
            logger.warning(f"Web search cache write failed: {e}")

    async def invalidate(self, query: str, engine: str) -> None:
        """Remove a cached entry."""
        try:
            from backend.redis_client import get_redis

            redis = await get_redis()
            key = self._cache_key(query, engine)
            await redis.delete(key)
        except Exception as e:
            logger.warning(f"Web search cache invalidation failed: {e}")
