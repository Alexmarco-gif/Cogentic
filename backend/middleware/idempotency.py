"""Idempotency middleware for write operations.

Prevents duplicate operations when requests are retried (network issues, timeouts).
Clients send `Idempotency-Key` header; server stores result for 24h.

Usage:
    @router.post("/briefs/generate")
    @idempotent(ttl=86400)
    async def generate_brief(...):
        ...
"""

import asyncio
import hashlib
import json
import logging
from functools import wraps
from typing import Callable

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from backend.redis_client import get_redis

logger = logging.getLogger(__name__)

IDEMPOTENCY_HEADER = "Idempotency-Key"
IDEMPOTENCY_PREFIX = "idempotency:"
_PROCESSING_SENTINEL = "__processing__"


def _build_redis_key(request: Request, idem_key: str) -> str:
    """Build org/user-scoped idempotency key to prevent cross-tenant collisions."""
    scope = "anon"
    token_payload = getattr(request.state, "token_payload", None)
    if token_payload:
        # Prefer org_id for multi-tenant isolation, fall back to user sub
        org_id = getattr(token_payload, "org_id", None) or (
            token_payload.get("org_id") if isinstance(token_payload, dict) else None
        )
        sub = getattr(token_payload, "sub", None) or (
            token_payload.get("sub") if isinstance(token_payload, dict) else None
        )
        scope = str(org_id) if org_id else (str(sub) if sub else "anon")
    return f"{IDEMPOTENCY_PREFIX}{scope}:{idem_key}"


def idempotent(ttl: int = 86400):
    """Decorator for idempotent endpoints.

    Uses Redis SET NX to atomically claim the idempotency key *before*
    executing the handler, preventing the TOCTOU race between GET and SET.

    Args:
        ttl: How long to cache the result (seconds). Default 24h.

    Raises:
        HTTPException 400: If Idempotency-Key header is missing
        HTTPException 409: If key is reused with different request body or still processing
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

            redis = await get_redis()
            redis_key = _build_redis_key(request, idem_key)

            # ── Step 1: Try to atomically claim the key ──────────────
            claimed = await redis.set(
                redis_key, _PROCESSING_SENTINEL, nx=True, ex=ttl
            )

            if not claimed:
                # Key already exists — either another request is processing,
                # or we have a cached result.
                cached = await redis.get(redis_key)

                if cached == _PROCESSING_SENTINEL:
                    # Another concurrent request is still executing.
                    # Wait a reasonable time for it to finish.
                    for _ in range(50):  # up to 5 seconds
                        await asyncio.sleep(0.1)
                        cached = await redis.get(redis_key)
                        if cached and cached != _PROCESSING_SENTINEL:
                            break
                    else:
                        raise HTTPException(
                            status_code=409,
                            detail="Duplicate request is still being processed. Retry later.",
                        )

                # We have a cached result — verify body hash matches
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
                    # Delete corrupt entry and fall through to re-execute
                    await redis.delete(redis_key)

            # ── Step 2: Execute the handler ──────────────────────────
            try:
                result = await func(*args, **kwargs)
            except Exception:
                # On failure, release the key so retries are possible
                await redis.delete(redis_key)
                raise

            # ── Step 3: Store result, replacing the sentinel ─────────
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
                await redis.set(redis_key, json.dumps(cache_data), ex=ttl)
                logger.info(f"Idempotency stored: {idem_key}")
            except Exception as e:
                logger.error(f"Failed to cache idempotency result: {e}")

            return result

        return wrapper

    return decorator
