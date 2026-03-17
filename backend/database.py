"""Database session management"""

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def _normalize_db_url(url: str) -> tuple[str, dict]:
    """Normalize a PostgreSQL URL for asyncpg.

    - Rewrites the scheme to postgresql+asyncpg if needed.
    - Converts ``?sslmode=require`` (psycopg2 / libpq syntax) to the
      asyncpg-compatible ``ssl`` connect_arg.
    - Strips all libpq-only query parameters that asyncpg's ``connect()``
      does not accept (e.g. ``channel_binding``, ``connect_timeout``, …).

    Returns the cleaned URL and a dict of extra connect_args.
    """
    # libpq / psycopg2 keywords that asyncpg does NOT accept as connect() kwargs.
    # These must be removed from the query string before the URL is handed to
    # SQLAlchemy's asyncpg dialect.
    _LIBPQ_ONLY_PARAMS = frozenset(
        {
            "channel_binding",
            "connect_timeout",
            "fallback_application_name",
            "gssencmode",
            "gsslib",
            "keepalives",
            "keepalives_count",
            "keepalives_idle",
            "keepalives_interval",
            "krbsrvname",
            "options",
            "sslcompression",
            "sslcrl",
            "sslcrldir",
            "target_session_attrs",
        }
    )

    # Fix scheme
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    ssl_connect_args: dict = {}

    # Convert sslmode → asyncpg ssl connect_arg
    if "sslmode" in qs:
        sslmode = qs.pop("sslmode")[0]
        if sslmode in ("require", "verify-ca", "verify-full"):
            import ssl as _ssl

            if sslmode == "require":
                ssl_connect_args["ssl"] = True
            else:
                ssl_ctx = _ssl.create_default_context()
                ssl_ctx.verify_mode = _ssl.CERT_REQUIRED
                ssl_connect_args["ssl"] = ssl_ctx
        elif sslmode == "disable":
            ssl_connect_args["ssl"] = False

    # Drop any remaining libpq-only params
    for param in _LIBPQ_ONLY_PARAMS:
        qs.pop(param, None)

    # Rebuild URL with cleaned query string
    new_qs = urlencode(qs, doseq=True)
    parsed = parsed._replace(query=new_qs)
    url = urlunparse(parsed)

    return url, ssl_connect_args


# Ensure database URL uses async driver (asyncpg)
database_url, _ssl_connect_args = _normalize_db_url(settings.database_url)

# Create async engine — pool sizes driven by config (settings.database_pool_size
# / settings.database_max_overflow).  The config defaults are tuned for
# 4 Gunicorn workers against Azure PostgreSQL Flexible Server.
engine = create_async_engine(
    database_url,
    echo=settings.debug,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=30,  # Wait 30s for connection from pool
    pool_recycle=600,  # Recycle connections every 10 min (Azure idle timeout)
    pool_pre_ping=True,  # Verify connections before using
    connect_args={
        "server_settings": {
            "application_name": "cogent_backend",
        },
        **_ssl_connect_args,
    },
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ── Read Replica Engine (for read-heavy dashboards / list endpoints) ──

_read_database_url, _read_ssl_connect_args = _normalize_db_url(
    settings.database_read_url or settings.database_url
)

read_engine = create_async_engine(
    _read_database_url,
    echo=settings.debug,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=30,
    pool_recycle=600,
    pool_pre_ping=True,
    connect_args={
        "server_settings": {
            "application_name": "cogent_backend_read",
        },
        **_read_ssl_connect_args,
    },
)

AsyncSessionLocalRead = async_sessionmaker(
    read_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# === QUERY PERFORMANCE MONITORING ===

from backend.observability import (
    db_query_duration_seconds,
    db_query_total,
    db_slow_query_total,
)


@event.listens_for(Engine, "before_cursor_execute", named=True)
def before_cursor_execute(**kw):
    """Track query start time"""
    conn = kw["conn"]
    conn.info.setdefault("query_start_time", []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute", named=True)
def after_cursor_execute(**kw):
    """Log slow queries (>100ms) and emit Prometheus metrics."""
    conn = kw["conn"]
    statement = kw["statement"]

    # Calculate query duration
    total_time = time.time() - conn.info["query_start_time"].pop(-1)
    duration_ms = total_time * 1000

    # Prometheus metrics
    db_query_total.inc()
    db_query_duration_seconds.observe(total_time)

    # N+1 detection — increment per-request counter
    try:
        from backend.middleware.n1_detection import increment_query_count

        increment_query_count()
    except Exception:
        pass

    # Log slow queries (sanitise to avoid leaking PII in bound parameters)
    if duration_ms > 100:
        db_slow_query_total.inc()
        # Only log the SQL statement text, never bound parameters
        safe_stmt = statement[:200].split("--")[0].strip() if statement else "<unknown>"
        logger.warning(
            "Slow query detected",
            extra={"duration_ms": round(duration_ms, 2), "statement_prefix": safe_stmt},
        )

    # Log all queries in debug mode
    if settings.debug and duration_ms > 10:
        safe_stmt_dbg = (
            statement[:150].split("--")[0].strip() if statement else "<unknown>"
        )
        logger.debug(
            "Query timing",
            extra={
                "duration_ms": round(duration_ms, 2),
                "statement_prefix": safe_stmt_dbg,
            },
        )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions (read-write, primary).

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_read() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for read-only database sessions (uses read replica).

    Routes to ``DATABASE_READ_URL`` when configured, otherwise falls back
    to the primary.  Use for heavy list/dashboard/feed queries that
    don't need write access.

    Usage:
        @app.get("/feed")
        async def feed(db: AsyncSession = Depends(get_db_read)):
            ...
    """
    async with AsyncSessionLocalRead() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context():
    """Context manager for database sessions outside FastAPI"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
