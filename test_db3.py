import asyncio
import ssl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import pool, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import async_engine_from_config
from backend.config import get_settings

settings = get_settings()
database_url = settings.database_url
print(f"Original URL: {database_url[:60]}...")

url = make_url(database_url)
print(f"Driver: {url.drivername}")

if url.drivername in ("postgresql", "postgres"):
    url = url.set(drivername="postgresql+asyncpg")

query = dict(url.query)
print(f"Query params before strip: {query}")
query.pop("sslmode", None)
query.pop("channel_binding", None)
url = url.set(query=query)
database_url = str(url)
print(f"Final URL: {database_url[:60]}...")

# Mimic exactly what env.py does
configuration = {"sqlalchemy.url": database_url}
print(f"Configuration: {configuration}")

async def test():
    try:
        connectable = async_engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            connect_args={"ssl": True},
        )
        async with connectable.connect() as connection:
            result = await connection.execute(text("SELECT current_database()"))
            print(f"SUCCESS: connected to {result.scalar()}")
        await connectable.dispose()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

asyncio.run(test())
