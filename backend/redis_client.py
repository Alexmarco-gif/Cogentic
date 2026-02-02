"""Redis connection management"""

from typing import Optional

import redis as sync_redis
import redis.asyncio as redis
from redis import Redis as SyncRedis
from redis.asyncio import Redis

from backend.config import get_settings

settings = get_settings()

# Global Redis connection pools
_redis_client: Optional[Redis] = None
_sync_redis_client: Optional[SyncRedis] = None


async def get_redis() -> Redis:
    """
    Get async Redis client singleton.
    
    Usage in FastAPI:
        redis_client = await get_redis()
        await redis_client.set("key", "value")
    """
    global _redis_client
    
    if _redis_client is None:
        _redis_client = await redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.redis_max_connections
        )
    
    return _redis_client


def get_redis_client() -> SyncRedis:
    """
    Get synchronous Redis client for RQ (Redis Queue).
    
    Note: RQ requires decode_responses=False because it handles
    its own serialization/deserialization of job data.
    
    Usage with RQ:
        from backend.redis_client import get_redis_client
        redis_conn = get_redis_client()
        queue = Queue(connection=redis_conn)
    """
    global _sync_redis_client
    
    if _sync_redis_client is None:
        _sync_redis_client = sync_redis.from_url(
            settings.redis_url,
            decode_responses=False,  # RQ handles its own serialization
            max_connections=settings.redis_max_connections
        )
    
    return _sync_redis_client


async def close_redis():
    """Close async Redis connection (call on app shutdown)"""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


def close_sync_redis():
    """Close sync Redis connection"""
    global _sync_redis_client
    
    if _sync_redis_client:
        _sync_redis_client.close()
        _sync_redis_client = None
