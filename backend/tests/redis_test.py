import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock
import pytest

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.asyncio
async def test_redis_operations(mock_redis):
    """Test Redis operations with mocked client"""
    with patch("backend.redis_client.get_redis", return_value=mock_redis):
        from backend.redis_client import get_redis

        redis = await get_redis()

        # Set a value
        await redis.set("test_key", "test_value")
        mock_redis.set.assert_called_with("test_key", "test_value")

        # Get the value
        value = await redis.get("test_key")
        assert value is not None

        # Test expiration
        await redis.setex("temp_key", 5, "expires_soon")
        mock_redis.setex.assert_called_with("temp_key", 5, "expires_soon")

        # Test counter (for rate limiting)
        await redis.incr("counter")
        await redis.incr("counter")
        mock_redis.incr.assert_called()

        # Clean up
        await redis.delete("test_key", "temp_key", "counter")
        mock_redis.delete.assert_called_with("test_key", "temp_key", "counter")


@pytest.mark.asyncio
async def test_redis_ping(mock_redis):
    """Test Redis connection ping"""
    with patch("backend.redis_client.get_redis", return_value=mock_redis):
        from backend.redis_client import get_redis

        redis = await get_redis()
        result = await redis.ping()
        assert result is True
