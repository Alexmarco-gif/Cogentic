"""Pytest configuration for backend tests"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

# Add project root to Python path so 'backend' module can be imported
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing without actual Redis connection"""
    redis_mock = AsyncMock()
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.get = AsyncMock(return_value=b"test_value")
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.ping = AsyncMock(return_value=True)
    return redis_mock
