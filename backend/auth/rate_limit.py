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
    # Check if request has auth context (set by get_current_user dependency)
    auth: AuthContext | None = getattr(request.state, "auth", None)

    if auth:
        # Use user_id for authenticated requests
        key = f"user:{auth.user_id}"
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
    auth: AuthContext | None = getattr(request.state, "auth", None)

    if not auth:
        # Public endpoints: 20/min per IP
        return "20/minute"

    # Super admins get highest limits
    if auth.is_super_admin:
        return "1000/minute"

    # Admins and owners get high limits
    if auth.is_admin_or_higher:
        return "1000/minute"

    # Regular authenticated users
    return "100/minute"


# Create limiter instance
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["100/minute"],  # Default for authenticated endpoints
    headers_enabled=True,  # Return X-RateLimit-* headers
    storage_uri="memory://",  # Use in-memory storage (can switch to Redis)
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
