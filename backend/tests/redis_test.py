import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from backend.redis_client import get_redis

async def test_redis():
    redis = await get_redis()
    
    # Set a value
    await redis.set("test_key", "test_value")
    print("✅ Set test_key")
    
    # Get the value
    value = await redis.get("test_key")
    print(f"✅ Retrieved: {value}")
    
    # Test expiration
    await redis.setex("temp_key", 5, "expires_soon")
    print("✅ Set temp_key with 5 second expiration")
    
    # Test counter (for rate limiting)
    await redis.incr("counter")
    await redis.incr("counter")
    count = await redis.get("counter")
    print(f"✅ Counter value: {count}")
    
    # Clean up
    await redis.delete("test_key", "temp_key", "counter")
    print("✅ Cleaned up test keys")
    
    print("\n🎉 Redis operations successful!")

asyncio.run(test_redis())
