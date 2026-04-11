"""
Rate limiting configuration using slowapi

Different rate limits based on authentication level:
- Public endpoints: 20/min per IP
- Authenticated endpoints: 100/min per user
- Admin endpoints: 1000/min per user
"""

import logging
from typing import Callable

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.auth.schemas import AuthContext

logger = logging.getLogger(__name__)


def get_rate_limit_key(request: Request) -> str:
    """
    Determine rate limit key based on authentication status.

    Strategy:
    - Authenticated users: Use user_id (allows higher limits)
    - Unauthenticated: Use IP address (lower limits for abuse prevention)
    """
    # Check if request has token payload (set by JWTMiddleware)
    token_payload = getattr(request.state, "token_payload", None)

    if token_payload and hasattr(token_payload, "sub"):
        # Use token subject (user ID) for authenticated requests
        key = f"user:{token_payload.sub}"
        logger.debug(f"Rate limit key: {key}")
        return key

    # Fallback to IP for unauthenticated requests
    ip = get_remote_address(request)
    logger.debug(f"Rate limit key: ip:{ip}")
    return f"ip:{ip}"


def get_rate_limit_for_user(request: Request) -> str:
    """
    Determine appropriate rate limit based on user role.

    Returns:
        Rate limit string (e.g., "100/minute")
    """
    token_payload = getattr(request.state, "token_payload", None)

    if not token_payload:
        # Public endpoints: 20/min per IP
        return "20/minute"

    # Check auth context if available (set by get_current_user dependency)
    auth: AuthContext | None = getattr(request.state, "auth", None)

    if auth:
        # Super admins get highest limits
        if auth.is_super_admin:
            return "1000/minute"

        # Admins and owners get high limits
        if auth.is_admin_or_higher:
            return "1000/minute"

    # Regular authenticated users
    return "100/minute"


# Create limiter instance with shared Redis storage
# This ensures rate limits are enforced consistently across all worker processes
from backend.config import get_settings

_settings = get_settings()

limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["100/minute"],  # Default for authenticated endpoints
    headers_enabled=True,  # Return X-RateLimit-* headers
    storage_uri=_settings.redis_url,  # Shared Redis storage for accurate cross-worker rate limiting
    in_memory_fallback_enabled=True,  # Degrade gracefully if Redis is temporarily unavailable
)


# Convenience decorators for common rate limits


def rate_limit_public(func: Callable) -> Callable:
    """Decorator for public endpoints (20/min per IP)"""
    return limiter.limit("20/minute")(func)


def rate_limit_authenticated(func: Callable) -> Callable:
    """Decorator for authenticated endpoints (100/min per user)"""
    return limiter.limit("100/minute")(func)


def rate_limit_admin(func: Callable) -> Callable:
    """Decorator for admin endpoints (1000/min)"""
    return limiter.limit("1000/minute")(func)


def rate_limit_dynamic(func: Callable) -> Callable:
    """Decorator that adapts rate limit based on user role"""
    return limiter.limit(get_rate_limit_for_user)(func)
