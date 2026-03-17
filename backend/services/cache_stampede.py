"""Cache stampede (thundering-herd) protection.

When a hot cache key expires, many concurrent requests may try to
regenerate the value simultaneously — a "cache stampede".  This module
provides a Redis-based lock that ensures only **one** caller computes
the new value while all others wait or receive the stale entry.

Usage:
    from backend.services.cache_stampede import cached_with_lock

    result = await cached_with_lock(
        key="synthesis:abc123",
        ttl=900,
        compute_fn=my_expensive_coroutine,
        lock_timeout=30,
    )

Algorithm (XFetch-inspired):
  1. GET key → if value exists and is NOT within the early-recompute
     window, return it immediately.
  2. Acquire a Redis SET NX lock (`{key}:lock`, 30 s TTL).
     - Winner: compute new value, SET key with TTL, release lock.
     - Losers: wait briefly, re-read key, return (possibly stale) value.
"""

import asyncio
import json
import logging
from collections.abc import Coroutine
from typing import Any, Callable

from backend.redis_client import get_redis

logger = logging.getLogger(__name__)

# Fraction of TTL remaining at which a background recompute is triggered.
# e.g. if TTL = 900 s, early recompute starts at 900 * 0.1 = 90 s remaining.
EARLY_RECOMPUTE_FRACTION = 0.10

# Maximum time (seconds) a loser will wait for the winner to finish.
LOCK_WAIT_MAX = 10.0
LOCK_POLL_INTERVAL = 0.15  # seconds between polls


async def cached_with_lock(
    *,
    key: str,
    ttl: int,
    compute_fn: Callable[[], Coroutine[Any, Any, Any]],
    lock_timeout: int = 30,
    serialize: Callable[[Any], str] = lambda v: json.dumps(v, default=str),
    deserialize: Callable[[str], Any] = json.loads,
) -> Any:
    """Get a cached value, recomputing with stampede protection.

    Args:
        key: Redis cache key.
        ttl: Time-to-live in seconds for the cached value.
        compute_fn: Async callable that produces the value on cache miss.
        lock_timeout: How long the recompute lock is held (seconds).
        serialize: Function to convert the value to a string for Redis.
        deserialize: Function to convert the Redis string back to a value.

    Returns:
        The cached or freshly computed value.
    """
    redis = await get_redis()

    # ── 1. Fast path: cache hit ──────────────────────────────────────
    cached_raw = await redis.get(key)
    if cached_raw is not None:
        remaining_ttl = await redis.ttl(key)
        # If well within TTL, return immediately
        if remaining_ttl > ttl * EARLY_RECOMPUTE_FRACTION:
            return deserialize(cached_raw)
        # Within early-recompute window → try to win the lock for
        # background refresh; if we lose, return stale value.
        acquired = await redis.set(
            f"{key}:lock",
            "1",
            nx=True,
            ex=lock_timeout,
        )
        if acquired:
            # Winner: recompute in background, return stale value now
            asyncio.create_task(
                _recompute_and_cache(
                    key,
                    ttl,
                    compute_fn,
                    serialize,
                    redis,
                )
            )
        return deserialize(cached_raw)

    # ── 2. Cache miss — compete for lock ─────────────────────────────
    acquired = await redis.set(
        f"{key}:lock",
        "1",
        nx=True,
        ex=lock_timeout,
    )

    if acquired:
        # Winner: compute, cache, release
        try:
            value = await compute_fn()
            await redis.setex(key, ttl, serialize(value))
            return value
        finally:
            await redis.delete(f"{key}:lock")
    else:
        # Loser: wait for the winner to populate the cache
        return await _wait_for_value(
            key,
            redis,
            deserialize,
            compute_fn,
            ttl,
            serialize,
        )


async def _recompute_and_cache(
    key: str,
    ttl: int,
    compute_fn: Callable[[], Coroutine[Any, Any, Any]],
    serialize: Callable[[Any], str],
    redis,
) -> None:
    """Background task: recompute value and update cache."""
    try:
        value = await compute_fn()
        await redis.setex(key, ttl, serialize(value))
    except Exception as e:
        logger.warning("cache_stampede_recompute_failed", key=key, error=str(e))
    finally:
        await redis.delete(f"{key}:lock")


async def _wait_for_value(
    key: str,
    redis,
    deserialize: Callable[[str], Any],
    compute_fn: Callable[[], Coroutine[Any, Any, Any]],
    ttl: int,
    serialize: Callable[[Any], str],
) -> Any:
    """Wait for the winner to populate the cache, with fallback."""
    waited = 0.0
    while waited < LOCK_WAIT_MAX:
        await asyncio.sleep(LOCK_POLL_INTERVAL)
        waited += LOCK_POLL_INTERVAL
        cached_raw = await redis.get(key)
        if cached_raw is not None:
            return deserialize(cached_raw)

    # Lock holder may have crashed — compute ourselves as a fallback
    logger.warning("cache_stampede_lock_timeout", key=key)
    value = await compute_fn()
    await redis.setex(key, ttl, serialize(value))
    return value
