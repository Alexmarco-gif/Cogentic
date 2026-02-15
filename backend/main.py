"""FastAPI main application"""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

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
from backend.database import engine
from backend.observability import (
    get_logger,
    http_request_duration_seconds,
    http_requests_total,
    init_observability,
)
from backend.redis_client import close_redis, get_redis
from backend.webhooks import auth0_router

settings = get_settings()
logger = get_logger(__name__)


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


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track request metrics for Prometheus"""

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

        # Extract endpoint (remove IDs for cleaner metrics)
        endpoint = request.url.path
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
    print("🚀 Starting Cogent API...")

    # Initialize observability
    init_observability(
        environment=settings.environment,
        version=settings.app_version,
        sentry_dsn=getattr(settings, "sentry_dsn", None),
        logtail_token=getattr(settings, "logtail_token", None),
        posthog_api_key=getattr(settings, "posthog_api_key", None),
    )

    # Test database connection
    try:
        async with engine.connect():
            logger.info("database_connected")
            print("✅ Database connected")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        print(f"❌ Database connection failed: {e}")

    # Test Redis connection
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("redis_connected")
        print("✅ Redis connected")
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        print(f"❌ Redis connection failed: {e}")

    logger.info("app_startup_complete", environment=settings.environment)
    print("✅ Auth system initialized")

    # Start signal acquisition scheduler
    try:
        from backend.signals.scheduler import get_scheduler

        scheduler = get_scheduler()
        scheduler.start()
        print("✅ Signal scheduler started")
    except Exception as e:
        logger.error("scheduler_start_failed", error=str(e))
        print(f"⚠️ Signal scheduler failed to start: {e}")

    # Start Situation Room WebSocket manager (Redis Pub/Sub listener)
    try:
        from backend.services.ws_manager import get_connection_manager

        ws_manager = get_connection_manager()
        await ws_manager.start_pubsub_listener()
        print("✅ Situation Room WebSocket manager started")
    except Exception as e:
        logger.error("ws_manager_start_failed", error=str(e))
        print(f"⚠️ WebSocket manager failed to start: {e}")

    yield

    # Shutdown
    logger.info("app_shutdown_started")
    print("🛑 Shutting down Cogent API...")

    # Stop scheduler
    try:
        from backend.signals.scheduler import get_scheduler

        scheduler = get_scheduler()
        scheduler.stop()
    except Exception:
        pass

    # Stop WebSocket manager
    try:
        from backend.services.ws_manager import get_connection_manager

        ws_manager = get_connection_manager()
        await ws_manager.stop_pubsub_listener()
    except Exception:
        pass

    await close_redis()
    await close_jwks_client()
    await engine.dispose()
    logger.info("app_shutdown_complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# Add rate limiter state
app.state.limiter = limiter

# Add middleware (order matters: first added = outermost in FastAPI)
# CORS must be FIRST (outermost) to handle preflight before JWT rejects
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(JWTMiddleware)

# Exception handlers
app.add_exception_handler(AuthError, auth_exception_handler)
app.add_exception_handler(ForbiddenError, forbidden_exception_handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include API routers
app.include_router(api_v1_router)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
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
    """Detailed health check"""
    # Test database
    db_healthy = False
    try:
        async with engine.connect():
            db_healthy = True
    except Exception:
        pass

    # Test Redis
    redis_healthy = False
    try:
        redis = await get_redis()
        await redis.ping()
        redis_healthy = True
    except Exception:
        pass

    return {
        "status": "healthy" if db_healthy and redis_healthy else "degraded",
        "version": settings.app_version,
        "environment": settings.environment,
        "services": {
            "database": "up" if db_healthy else "down",
            "redis": "up" if redis_healthy else "down",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
