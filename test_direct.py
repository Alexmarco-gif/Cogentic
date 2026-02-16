import asyncio, ssl, asyncpg

async def test():
    ctx = ssl.create_default_context()
    try:
        conn = await asyncpg.connect(
            "postgresql://neondb_owner:npg_L47OdNMBlcvG@ep-morning-sound-ag7guaxz.c-2.eu-central-1.aws.neon.tech/neondb",
            ssl=ctx
        )
        v = await conn.fetchval("SELECT version()")
        print(f"DIRECT: SUCCESS - {v[:60]}")
        await conn.close()
    except Exception as e:
        print(f"DIRECT: FAILED - {e}")

asyncio.run(test())
