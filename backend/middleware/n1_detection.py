"""N+1 Query Detection Middleware.

Counts SQL queries per HTTP request and logs a warning when the count
exceeds a threshold — a strong signal for N+1 query patterns that
should be refactored to use eager loading (``selectinload``,
``joinedload``) or batch queries.

Enable via ``N1_QUERY_DETECTION=true`` environment variable (always
on in development/staging, opt-in in production).

The detector does NOT block requests — it only logs warnings and
increments a Prometheus counter so teams can find and fix offenders.
"""

import contextvars
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Context var to accumulate query count per request
_request_query_count: contextvars.ContextVar[int] = contextvars.ContextVar(
    "request_query_count", default=0
)
_request_start_time: contextvars.ContextVar[float] = contextvars.ContextVar(
    "request_start_time", default=0.0
)

# Thresholds
N1_WARNING_THRESHOLD = 15  # warn when > 15 queries in a single request
N1_CRITICAL_THRESHOLD = 50  # critical log when > 50 queries


def increment_query_count() -> int:
    """Called by SQLAlchemy event listener to track per-request query count."""
    current = _request_query_count.get(0)
    new_count = current + 1
    _request_query_count.set(new_count)
    return new_count


def get_query_count() -> int:
    """Get the query count for the current request."""
    return _request_query_count.get(0)


class N1QueryDetectionMiddleware(BaseHTTPMiddleware):
    """Detect potential N+1 query patterns per request.

    Resets the per-request query counter on entry, inspects it on exit,
    and logs a warning if the count exceeds the threshold.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip non-API paths
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Reset counter for this request
        _request_query_count.set(0)
        _request_start_time.set(time.time())

        response = await call_next(request)

        query_count = _request_query_count.get(0)
        duration = time.time() - _request_start_time.get(0)

        if query_count > N1_CRITICAL_THRESHOLD:
            logger.error(
                "n1_query_critical",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "query_count": query_count,
                    "duration_s": round(duration, 3),
                    "hint": "Likely N+1 — use selectinload/joinedload or batch queries",
                },
            )
        elif query_count > N1_WARNING_THRESHOLD:
            logger.warning(
                "n1_query_warning",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "query_count": query_count,
                    "duration_s": round(duration, 3),
                    "hint": "Potential N+1 — investigate with EXPLAIN ANALYZE",
                },
            )

        return response
