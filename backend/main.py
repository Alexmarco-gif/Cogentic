"""FastAPI main application"""

import re
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from backend.api.v1 import api_v1_router
from backend.auth.exceptions import AuthError, ForbiddenError
from backend.auth.jwks import close_jwks_client
from backend.auth.middleware import (
    JWTMiddleware,
    auth_exception_handler,
    forbidden_exception_handler,
)
from backend.auth.rate_limit import limiter
from backend.config import get_settings
from backend.database import engine, read_engine
from backend.jobs.pricing_scheduler import start_pricing_jobs, stop_pricing_jobs
from backend.observability import (
    collect_db_pool_metrics,
    collect_job_queue_metrics,
    collect_redis_metrics,
    get_logger,
    http_request_duration_seconds,
    http_requests_total,
    init_observability,
)
from backend.redis_client import close_redis, close_sync_redis, get_redis
from backend.webhooks import auth0_router

settings = get_settings()
logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add defensive security headers to every API response."""

    _HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Cache-Control": "no-store",
    }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in self._HEADERS.items():
            response.headers.setdefault(header, value)
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracing"""

    async def dispatch(self, request: Request, call_next):
        # Generate or use existing request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store in request state
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds the configured limit.

    This prevents oversized uploads from consuming memory before FastAPI
    parses the body.  The limit is controlled via ``MAX_REQUEST_BODY_BYTES``
    (default 10 MB).
    """

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_request_body_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Payload Too Large",
                    "message": (
                        f"Request body exceeds {settings.max_request_body_bytes} bytes"
                    ),
                },
            )
        return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track request metrics for Prometheus"""

    # Pre-compiled regex for UUID and numeric path segments
    _UUID_RE = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        re.IGNORECASE,
    )
    _NUMERIC_SEGMENT_RE = re.compile(r"/\d+(?=/|$)")

    @staticmethod
    def _sanitize_endpoint(path: str) -> str:
        """Replace UUIDs and numeric IDs with placeholders to bound label cardinality."""
        path = MetricsMiddleware._UUID_RE.sub("{id}", path)
        path = MetricsMiddleware._NUMERIC_SEGMENT_RE.sub("/{id}", path)
        return path

    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        # Start timing
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Extract endpoint (sanitize IDs for bounded cardinality)
        endpoint = self._sanitize_endpoint(request.url.path)
        method = request.method
        status_code = response.status_code

        # Record metrics
        http_requests_total.labels(
            method=method, endpoint=endpoint, status=str(status_code)
        ).inc()

        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
            duration
        )

        # Log slow requests
        if duration > 2.0:
            logger.warning(
                "slow_request",
                method=method,
                endpoint=endpoint,
                duration=duration,
                status_code=status_code,
                request_id=request.state.request_id,
            )

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager"""
    # Startup
    logger.info(
        "app_starting", environment=settings.environment, version=settings.app_version
    )

    # Initialize observability
    init_observability(
        environment=settings.environment,
        version=settings.app_version,
        sentry_dsn=getattr(settings, "sentry_dsn", None),
        logtail_token=getattr(settings, "logtail_token", None),
        posthog_api_key=getattr(settings, "posthog_api_key", None),
        posthog_host=getattr(settings, "posthog_host", None),
    )

    # Test database connection
    db_ok = False
    try:
        async with engine.connect():
            logger.info("database_connected")
            db_ok = True
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        if settings.require_healthy_db_on_startup:
            raise RuntimeError(f"Cannot start: database unreachable — {e}") from e

    # Test Redis connection
    redis_ok = False
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("redis_connected")
        redis_ok = True
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        if settings.require_healthy_redis_on_startup:
            raise RuntimeError(f"Cannot start: Redis unreachable — {e}") from e

    logger.info(
        "app_startup_complete",
        environment=settings.environment,
        db_healthy=db_ok,
        redis_healthy=redis_ok,
    )

    # Start signal acquisition scheduler
    try:
        from backend.signals.scheduler import get_scheduler

        scheduler = get_scheduler()
        scheduler.start()
        logger.info("scheduler_started")
    except Exception as e:
        logger.error("scheduler_start_failed", error=str(e))

    try:
        start_pricing_jobs()
        logger.info("pricing_scheduler_started")
    except Exception as e:
        logger.error("pricing_scheduler_start_failed", error=str(e))

    # Start Situation Room WebSocket manager (Redis Pub/Sub listener)
    try:
        from backend.services.ws_manager import get_connection_manager

        ws_manager = get_connection_manager()
        await ws_manager.start_pubsub_listener()
        logger.info("ws_manager_started")
    except Exception as e:
        logger.error("ws_manager_start_failed", error=str(e))

    yield

    # Shutdown
    logger.info("app_shutdown_started")

    # Stop scheduler
    try:
        from backend.signals.scheduler import get_scheduler

        scheduler = get_scheduler()
        scheduler.stop()
    except Exception as e:
        logger.error("scheduler_stop_failed", error=str(e))

    try:
        stop_pricing_jobs()
    except Exception as e:
        logger.error("pricing_scheduler_stop_failed", error=str(e))

    # Stop WebSocket manager
    try:
        from backend.services.ws_manager import get_connection_manager

        ws_manager = get_connection_manager()
        await ws_manager.stop_pubsub_listener()
    except Exception as e:
        logger.error("ws_manager_stop_failed", error=str(e))

    await close_redis()
    close_sync_redis()
    await close_jwks_client()
    await engine.dispose()
    await read_engine.dispose()
    logger.info("app_shutdown_complete")


_is_production = settings.environment.lower() in ("production", "staging")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    # Disable interactive docs in production to reduce attack surface
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# Add rate limiter state
app.state.limiter = limiter

# Add middleware (order matters: first added = outermost in FastAPI)
# CORS must be FIRST (outermost) to handle preflight before JWT rejects
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "Accept",
    ],
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestBodyLimitMiddleware)
app.add_middleware(MetricsMiddleware)

# N+1 query detection (inside metrics so it has a request context)
from backend.middleware.n1_detection import N1QueryDetectionMiddleware  # noqa: E402

app.add_middleware(N1QueryDetectionMiddleware)
app.add_middleware(JWTMiddleware)

# Exception handlers
app.add_exception_handler(AuthError, auth_exception_handler)
app.add_exception_handler(ForbiddenError, forbidden_exception_handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include API routers
app.include_router(api_v1_router)


# Prometheus metrics endpoint (IP-restricted when METRICS_ALLOWED_IPS is set)
@app.get("/metrics", include_in_schema=False)
@app.head("/metrics", include_in_schema=False)
async def metrics_endpoint(request: Request):
    """Serve Prometheus metrics, restricted by IP allowlist when configured.

    Collects point-in-time gauge snapshots (DB pool, Redis, job queues)
    on every scrape so that values are always fresh.
    """
    allowed = settings.metrics_allowed_ips_list
    if _is_production and not allowed:
        logger.error(
            "metrics_access_unconfigured",
            environment=settings.environment,
        )
        return JSONResponse(
            status_code=403,
            content={
                "error": "Forbidden",
                "message": "Metrics access is disabled until METRICS_ALLOWED_IPS is configured",
            },
        )

    if allowed:
        client_ip = request.client.host if request.client else None
        if client_ip not in allowed:
            logger.warning(
                "metrics_access_denied",
                client_ip=client_ip,
                allowed=allowed,
            )
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden", "message": "Access denied"},
            )

    # ── Snapshot gauge metrics ────────────────────────────────────
    try:
        collect_db_pool_metrics(engine, read_engine)
    except Exception:
        pass
    try:
        redis = await get_redis()
        await collect_redis_metrics(redis)
    except Exception:
        pass
    try:
        collect_job_queue_metrics()
    except Exception:
        pass

    return StarletteResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


app.include_router(auth0_router)  # Webhooks (no JWT middleware required)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    """Detailed health check for container orchestrators.

    Returns HTTP 200 when all critical services are reachable, or
    HTTP 503 (Service Unavailable) when any dependency is down so that
    load-balancers can route traffic away from unhealthy instances.
    """
    # Test database
    db_healthy = False
    db_latency_ms: float | None = None
    try:
        t0 = time.time()
        async with engine.connect():
            db_healthy = True
        db_latency_ms = round((time.time() - t0) * 1000, 1)
    except Exception:
        pass

    # Test Redis
    redis_healthy = False
    redis_latency_ms: float | None = None
    try:
        t0 = time.time()
        redis = await get_redis()
        await redis.ping()
        redis_healthy = True
        redis_latency_ms = round((time.time() - t0) * 1000, 1)
    except Exception:
        pass

    all_healthy = db_healthy and redis_healthy
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "degraded",
            "version": settings.app_version,
            "environment": settings.environment,
            "services": {
                "database": {
                    "status": "up" if db_healthy else "down",
                    "latency_ms": db_latency_ms,
                },
                "redis": {
                    "status": "up" if redis_healthy else "down",
                    "latency_ms": redis_latency_ms,
                },
            },
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
