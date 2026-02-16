import asyncio
import ssl
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine

DB_URL = "postgresql+asyncpg://neondb_owner:npg_L47OdNMBlcvG@ep-morning-sound-ag7guaxz-pooler.c-2.eu-central-1.aws.neon.tech/neondb"

async def test():
    # Test 1: ssl=True (what env.py currently uses)
    try:
        engine = create_async_engine(DB_URL, poolclass=pool.NullPool, connect_args={"ssl": True})
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"Test 1 (ssl=True): SUCCESS - {result.scalar()}")
        await engine.dispose()
    except Exception as e:
        print(f"Test 1 (ssl=True): FAILED - {e}")

    # Test 2: ssl context
    try:
        ctx = ssl.create_default_context()
        engine = create_async_engine(DB_URL, poolclass=pool.NullPool, connect_args={"ssl": ctx})
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"Test 2 (ssl context): SUCCESS - {result.scalar()}")
        await engine.dispose()
    except Exception as e:
        print(f"Test 2 (ssl context): FAILED - {e}")

    # Test 3: ssl='require' string
    try:
        engine = create_async_engine(DB_URL, poolclass=pool.NullPool, connect_args={"ssl": "require"})
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"Test 3 (ssl='require'): SUCCESS - {result.scalar()}")
        await engine.dispose()
    except Exception as e:
        print(f"Test 3 (ssl='require'): FAILED - {e}")

asyncio.run(test())
