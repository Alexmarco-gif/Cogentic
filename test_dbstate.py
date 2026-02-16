"""Check database state and locks after failed migrations."""
import asyncio, ssl, asyncpg

async def check():
    ctx = ssl.create_default_context()
    conn = await asyncpg.connect(
        "postgresql://neondb_owner:npg_L47OdNMBlcvG@ep-morning-sound-ag7guaxz.c-2.eu-central-1.aws.neon.tech/neondb",
        ssl=ctx
    )
    
    # Check alembic_version table
    try:
        rows = await conn.fetch("SELECT * FROM alembic_version")
        print(f"alembic_version: {rows}")
    except Exception as e:
        print(f"alembic_version table: {e}")
    
    # Check for locks
    locks = await conn.fetch("""
        SELECT pid, state, wait_event_type, wait_event, query 
        FROM pg_stat_activity 
        WHERE datname = current_database() AND pid != pg_backend_pid()
    """)
    print(f"\nActive connections: {len(locks)}")
    for l in locks:
        print(f"  PID={l['pid']} state={l['state']} wait={l['wait_event_type']}:{l['wait_event']} query={l['query'][:100]}")
    
    # Check existing tables
    tables = await conn.fetch("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' ORDER BY tablename
    """)
    print(f"\nExisting tables ({len(tables)}):")
    for t in tables:
        print(f"  {t['tablename']}")
    
    await conn.close()

asyncio.run(check())
