"""Database session management"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

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

# Create async engine with Neon-optimized settings
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    # Neon serverless optimizations
    pool_size=5,              # Small pool for serverless (Neon has connection limits)
    max_overflow=10,          # Burst capacity for traffic spikes
    pool_timeout=30,          # Wait 30s for connection from pool
    pool_recycle=3600,        # Recycle connections after 1 hour (Neon idle timeout)
    pool_pre_ping=True,       # Verify connections before using
    connect_args={
        "server_settings": {
            "application_name": "cogent_backend",
        }
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


# === QUERY PERFORMANCE MONITORING ===

@event.listens_for(Engine, "before_cursor_execute", named=True)
def before_cursor_execute(**kw):
    """Track query start time"""
    conn = kw['conn']
    conn.info.setdefault('query_start_time', []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute", named=True)
def after_cursor_execute(**kw):
    """Log slow queries (>100ms)"""
    conn = kw['conn']
    statement = kw['statement']
    
    # Calculate query duration
    total_time = time.time() - conn.info['query_start_time'].pop(-1)
    duration_ms = total_time * 1000
    
    # Log slow queries
    if duration_ms > 100:
        logger.warning(
            f"Slow query detected ({duration_ms:.2f}ms): {statement[:200]}..."
        )
    
    # Log all queries in debug mode
    if settings.debug and duration_ms > 10:
        logger.debug(f"Query took {duration_ms:.2f}ms: {statement[:150]}...")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
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
