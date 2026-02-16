import asyncio
import ssl
import asyncpg

async def test():
    url = "postgresql://neondb_owner:npg_L47OdNMBlcvG@ep-morning-sound-ag7guaxz-pooler.c-2.eu-central-1.aws.neon.tech/neondb"
    
    # Test 1: ssl context
    try:
        ctx = ssl.create_default_context()
        conn = await asyncpg.connect(url, ssl=ctx)
        v = await conn.fetchval("SELECT version()")
        print(f"SUCCESS with ssl context: {v[:50]}")
        await conn.close()
    except Exception as e:
        print(f"FAILED with ssl context: {e}")
    
    # Test 2: ssl=True
    try:
        conn = await asyncpg.connect(url, ssl=True)
        v = await conn.fetchval("SELECT version()")
        print(f"SUCCESS with ssl=True: {v[:50]}")
        await conn.close()
    except Exception as e:
        print(f"FAILED with ssl=True: {e}")

    # Test 3: sslmode in URL
    try:
        conn = await asyncpg.connect(url + "?sslmode=require")
        v = await conn.fetchval("SELECT version()")
        print(f"SUCCESS with sslmode=require: {v[:50]}")
        await conn.close()
    except Exception as e:
        print(f"FAILED with sslmode=require: {e}")

asyncio.run(test())
