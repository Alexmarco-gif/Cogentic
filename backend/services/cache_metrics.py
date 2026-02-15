"""Cache Metrics - Track cache hit rates and efficiency.

Monitors Redis cache performance for optimization insights.
"""

import logging
import time
from typing import Any

from backend.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Lazy-initialized Redis client
_redis_client = None


def _get_redis():
    """Lazy initialization of sync Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = get_redis_client()
    return _redis_client


class CacheMetrics:
    """Track cache hit/miss rates per service."""

    @staticmethod
    def record_hit(cache_key: str, operation: str):
        """Record cache hit."""
        today = time.strftime("%Y-%m-%d")
        key = f"cache_metrics:{today}:{operation}:hits"
        _get_redis().incr(key)
        _get_redis().expire(key, 172800)  # 48 hours

    @staticmethod
    def record_miss(cache_key: str, operation: str):
        """Record cache miss."""
        today = time.strftime("%Y-%m-%d")
        key = f"cache_metrics:{today}:{operation}:misses"
        _get_redis().incr(key)
        _get_redis().expire(key, 172800)

    @staticmethod
    def get_stats(operation: str) -> dict[str, Any]:
        """Get cache statistics for an operation."""
        today = time.strftime("%Y-%m-%d")
        hits_key = f"cache_metrics:{today}:{operation}:hits"
        misses_key = f"cache_metrics:{today}:{operation}:misses"

        redis = _get_redis()
        hits = int(redis.get(hits_key) or 0)
        misses = int(redis.get(misses_key) or 0)
        total = hits + misses

        if total == 0:
            return {
                "operation": operation,
                "hits": 0,
                "misses": 0,
                "total": 0,
                "hit_rate": 0.0,
            }

        return {
            "operation": operation,
            "hits": hits,
            "misses": misses,
            "total": total,
            "hit_rate": round((hits / total) * 100, 1),
        }

    @staticmethod
    def get_all_stats() -> list[dict[str, Any]]:
        """Get cache stats for all operations."""
        operations = ["synthesis", "search", "recommendations"]
        return [CacheMetrics.get_stats(op) for op in operations]


# SLO Targets
CACHE_HIT_TARGET = 70.0  # 70% hit rate target for cost savings
