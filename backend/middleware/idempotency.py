"""Idempotency middleware for write operations.

Prevents duplicate operations when requests are retried (network issues, timeouts).
Clients send `Idempotency-Key` header; server stores result for 24h.

Usage:
    @router.post("/briefs/generate")
    @idempotent(ttl=86400)
    async def generate_brief(...):
        ...
"""

import hashlib
import json
import logging
from functools import wraps
from typing import Callable

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from backend.redis_client import get_redis_client

logger = logging.getLogger(__name__)

IDEMPOTENCY_HEADER = "Idempotency-Key"
IDEMPOTENCY_PREFIX = "idempotency:"


def idempotent(ttl: int = 86400):
    """Decorator for idempotent endpoints.

    Args:
        ttl: How long to cache the result (seconds). Default 24h.

    Raises:
        HTTPException 400: If Idempotency-Key header is missing
        HTTPException 409: If key is reused with different request body
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from FastAPI dependency injection
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for kwarg_val in kwargs.values():
                    if isinstance(kwarg_val, Request):
                        request = kwarg_val
                        break

            if not request:
                # No request found, skip idempotency check
                return await func(*args, **kwargs)

            # Get idempotency key from header
            idem_key = request.headers.get(IDEMPOTENCY_HEADER)
            if not idem_key:
                # Optional: enforce idempotency key for POST/PUT/PATCH
                if request.method in {"POST", "PUT", "PATCH"}:
                    logger.warning(
                        f"Idempotent endpoint called without {IDEMPOTENCY_HEADER}"
                    )
                # Allow call without key (not recommended for production)
                return await func(*args, **kwargs)

            redis = get_redis_client()
            redis_key = f"{IDEMPOTENCY_PREFIX}{idem_key}"

            # Check if we've seen this key before
            cached = redis.get(redis_key)
            if cached:
                # Verify request body hash matches (防止 key reuse with different data)
                try:
                    body_bytes = await request.body()
                    body_hash = hashlib.sha256(body_bytes).hexdigest()

                    cached_data = json.loads(cached)
                    if cached_data.get("body_hash") != body_hash:
                        raise HTTPException(
                            status_code=409,
                            detail="Idempotency key conflict: same key, different request body",
                        )

                    # Return cached response
                    logger.info(f"Idempotency hit: {idem_key}")
                    return JSONResponse(
                        content=cached_data["response"],
                        status_code=cached_data["status_code"],
                        headers={"X-Idempotency-Replay": "true"},
                    )
                except json.JSONDecodeError:
                    logger.error(f"Corrupted idempotency cache for key {idem_key}")
                    # Fall through to re-execute

            # Execute the actual endpoint
            result = await func(*args, **kwargs)

            # Cache the result
            try:
                body_bytes = await request.body()
                body_hash = hashlib.sha256(body_bytes).hexdigest()

                # Extract response data
                if isinstance(result, JSONResponse):
                    status_code = result.status_code
                    response_body = json.loads(result.body.decode())
                elif hasattr(result, "model_dump"):
                    # Pydantic model
                    status_code = 200
                    response_body = result.model_dump()
                else:
                    # Assume dict or serializable
                    status_code = 200
                    response_body = result

                cache_data = {
                    "body_hash": body_hash,
                    "response": response_body,
                    "status_code": status_code,
                }
                redis.setex(redis_key, ttl, json.dumps(cache_data))
                logger.info(f"Idempotency stored: {idem_key}")
            except Exception as e:
                logger.error(f"Failed to cache idempotency result: {e}")

            return result

        return wrapper

    return decorator
