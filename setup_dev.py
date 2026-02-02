"""Development setup script"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent))

from backend.config import get_settings
from backend.database import engine
from backend.models import Base
from backend.redis_client import get_redis


async def check_database():
    """Test database connection"""
    print("🔍 Checking database connection...")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(sa.text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Database connected: {version}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n📝 Make sure:")
        print("  1. DATABASE_URL is set in .env")
        print("  2. Database is accessible")
        print("  3. For local dev: docker-compose up -d postgres")
        return False


async def check_redis():
    """Test Redis connection"""
    print("\n🔍 Checking Redis connection...")
    try:
        redis = await get_redis()
        await redis.ping()
        info = await redis.info("server")
        print(f"✅ Redis connected: v{info.get('redis_version', 'unknown')}")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("\n📝 Make sure:")
        print("  1. REDIS_URL is set in .env")
        print("  2. Redis is running: docker-compose up -d redis")
        return False


async def create_tables():
    """Create database tables"""
    print("\n🔨 Creating database tables...")
    try:
        async with engine.begin() as conn:
            # Enable pgvector extension
            await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database tables created")
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        print("\n📝 Better approach: Use Alembic migrations")
        print("  Run: alembic upgrade head")
        return False


async def main():
    """Run all setup checks"""
    print("=" * 50)
    print("🚀 Cogent Backend Setup")
    print("=" * 50)
    
    # Check .env file
    env_path = Path(".env")
    if not env_path.exists():
        print("⚠️  .env file not found")
        print("📝 Creating .env from .env.example...")
        try:
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ .env created - PLEASE EDIT WITH YOUR CREDENTIALS")
            return
        except Exception as e:
            print(f"❌ Failed to create .env: {e}")
            return
    
    print("✅ .env file found")
    
    # Load settings
    try:
        settings = get_settings()
        print(f"✅ Configuration loaded: {settings.environment} environment")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        print("📝 Check your .env file for errors")
        return
    
    # Check connections
    db_ok = await check_database()
    redis_ok = await check_redis()
    
    if not (db_ok and redis_ok):
        print("\n❌ Setup incomplete - fix issues above")
        return
    
    print("\n" + "=" * 50)
    print("✅ All checks passed!")
    print("=" * 50)
    print("\n📝 Next steps:")
    print("  1. Run migrations: alembic upgrade head")
    print("  2. Start backend: uvicorn backend.main:app --reload")
    print("  3. Visit API docs: http://localhost:8000/docs")


if __name__ == "__main__":
    import sqlalchemy as sa
    asyncio.run(main())
