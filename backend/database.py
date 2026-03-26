"""Database session management."""

import logging
import time
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.config import Settings, get_settings
from backend.observability import (
    db_query_duration_seconds,
    db_query_total,
    db_slow_query_total,
)

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_read_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_read_session_factory: async_sessionmaker[AsyncSession] | None = None


def _settings() -> Settings:
    """Return cached application settings."""
    return get_settings()


def _normalize_db_url(url: str) -> tuple[str, dict]:
    """Normalize a PostgreSQL URL for asyncpg.

    - Rewrites the scheme to postgresql+asyncpg if needed.
    - Converts ``?sslmode=require`` (psycopg2 / libpq syntax) to the
      asyncpg-compatible ``ssl`` connect_arg.
    - Strips all libpq-only query parameters that asyncpg's ``connect()``
      does not accept.
    """
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

    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    ssl_connect_args: dict = {}

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

    for param in _LIBPQ_ONLY_PARAMS:
        qs.pop(param, None)

    new_qs = urlencode(qs, doseq=True)
    parsed = parsed._replace(query=new_qs)
    url = urlunparse(parsed)

    return url, ssl_connect_args


def _build_engine(
    url: str,
    ssl_connect_args: dict,
    *,
    application_name: str,
) -> AsyncEngine:
    """Create a configured async SQLAlchemy engine."""
    settings = _settings()
    return create_async_engine(
        url,
        echo=settings.debug,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=30,
        pool_recycle=600,
        pool_pre_ping=True,
        connect_args={
            "server_settings": {"application_name": application_name},
            **ssl_connect_args,
        },
    )


def get_engine() -> AsyncEngine:
    """Return the lazily-created primary async engine."""
    global _engine
    if _engine is None:
        settings = _settings()
        database_url, ssl_connect_args = _normalize_db_url(settings.database_url)
        _engine = _build_engine(
            database_url,
            ssl_connect_args,
            application_name="cogent_backend",
        )
    return _engine


def get_read_engine() -> AsyncEngine:
    """Return the lazily-created read-replica async engine."""
    global _read_engine
    if _read_engine is None:
        settings = _settings()
        database_url, ssl_connect_args = _normalize_db_url(
            settings.database_read_url or settings.database_url
        )
        _read_engine = _build_engine(
            database_url,
            ssl_connect_args,
            application_name="cogent_backend_read",
        )
    return _read_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the lazily-created primary session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


def get_async_read_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the lazily-created read session factory."""
    global _read_session_factory
    if _read_session_factory is None:
        _read_session_factory = async_sessionmaker(
            get_read_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _read_session_factory


class _LazyEngineProxy:
    """Expose a lazy engine behind the existing module-level API."""

    def __init__(self, factory: Callable[[], AsyncEngine]):
        self._factory = factory

    def __getattr__(self, name: str):
        return getattr(self._factory(), name)

    def __repr__(self) -> str:
        return repr(self._factory())


class _LazySessionFactoryProxy:
    """Expose a lazy sessionmaker behind the existing module-level API."""

    def __init__(self, factory: Callable[[], async_sessionmaker[AsyncSession]]):
        self._factory = factory

    def __call__(self, *args, **kwargs):
        return self._factory()(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self._factory(), name)

    def __repr__(self) -> str:
        return repr(self._factory())


engine = _LazyEngineProxy(get_engine)
read_engine = _LazyEngineProxy(get_read_engine)
AsyncSessionLocal = _LazySessionFactoryProxy(get_async_session_factory)
AsyncSessionLocalRead = _LazySessionFactoryProxy(get_async_read_session_factory)
async_session_maker = AsyncSessionLocal


@event.listens_for(Engine, "before_cursor_execute", named=True)
def before_cursor_execute(**kw):
    """Track query start time."""
    conn = kw["conn"]
    conn.info.setdefault("query_start_time", []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute", named=True)
def after_cursor_execute(**kw):
    """Log slow queries (>100ms) and emit Prometheus metrics."""
    conn = kw["conn"]
    statement = kw["statement"]

    total_time = time.time() - conn.info["query_start_time"].pop(-1)
    duration_ms = total_time * 1000

    db_query_total.inc()
    db_query_duration_seconds.observe(total_time)

    try:
        from backend.middleware.n1_detection import increment_query_count

        increment_query_count()
    except Exception:
        pass

    if duration_ms > 100:
        db_slow_query_total.inc()
        safe_stmt = statement[:200].split("--")[0].strip() if statement else "<unknown>"
        logger.warning(
            "Slow query detected",
            extra={"duration_ms": round(duration_ms, 2), "statement_prefix": safe_stmt},
        )

    if _settings().debug and duration_ms > 10:
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
    """FastAPI dependency for primary read-write database sessions."""
    async with get_async_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_read() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for read-only database sessions."""
    async with get_async_read_session_factory()() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context():
    """Context manager for database sessions outside FastAPI."""
    async with get_async_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
