"""
Mocked service tests — Redis-dependent services with AsyncMock Redis.

Tests:
  - CircuitBreaker (circuit_breaker.py)
  - CacheMetrics (cache_metrics.py)
  - SLOMetrics (slo_metrics.py)
  - CostTracker (cost_tracker.py)

All Redis calls are mocked via unittest.mock.patch on backend.redis_client.get_redis.
"""

import time
from unittest.mock import patch
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio


# =====================================================================
#  FakeRedis — in-memory dict backed async mock
# =====================================================================


class FakeRedis:
    """Minimal in-memory Redis mock supporting the operations used by
    CircuitBreaker, CacheMetrics, SLOMetrics, and CostTracker."""

    def __init__(self):
        self._store: dict[str, str | int | float] = {}
        self._sorted_sets: dict[str, dict[str, float]] = {}
        self._expiries: dict[str, int] = {}

    async def get(self, key: str):
        val = self._store.get(key)
        if val is not None:
            return str(val).encode() if not isinstance(val, bytes) else val
        return None

    async def set(self, key: str, value, ex: int | None = None, nx: bool = False):
        if nx and key in self._store:
            return None  # nx: only set if not exists
        self._store[key] = value
        if ex:
            self._expiries[key] = ex
        return True

    async def incr(self, key: str):
        current = int(self._store.get(key, 0))
        current += 1
        self._store[key] = current
        return current

    async def incrby(self, key: str, amount: int):
        current = int(self._store.get(key, 0))
        current += amount
        self._store[key] = current
        return current

    async def expire(self, key: str, seconds: int):
        self._expiries[key] = seconds
        return True

    async def delete(self, *keys):
        for k in keys:
            self._store.pop(k, None)
            self._sorted_sets.pop(k, None)
        return len(keys)

    async def zadd(self, key: str, mapping: dict[str, float]):
        if key not in self._sorted_sets:
            self._sorted_sets[key] = {}
        self._sorted_sets[key].update(mapping)
        return len(mapping)

    async def zrange(self, key: str, start: int, stop: int, withscores: bool = False):
        ss = self._sorted_sets.get(key, {})
        sorted_items = sorted(ss.items(), key=lambda x: x[1])
        # Handle negative stop (-1 = all)
        if stop < 0:
            stop = len(sorted_items) + stop + 1
        else:
            stop = stop + 1
        sliced = sorted_items[start:stop]
        if withscores:
            return [(m.encode() if isinstance(m, str) else m, s) for m, s in sliced]
        return [m.encode() if isinstance(m, str) else m for m, _ in sliced]

    async def zremrangebyrank(self, key: str, start: int, stop: int):
        ss = self._sorted_sets.get(key, {})
        sorted_members = sorted(ss.items(), key=lambda x: x[1])
        if stop < 0:
            stop = len(sorted_members) + stop + 1
        else:
            stop = stop + 1
        to_remove = sorted_members[start:stop]
        for member, _ in to_remove:
            ss.pop(member, None)
        return len(to_remove)

    def pipeline(self):
        return FakeRedisPipeline(self)


class FakeRedisPipeline:
    """Minimal pipeline mock — queues operations and executes them."""

    def __init__(self, redis: FakeRedis):
        self._redis = redis
        self._ops: list = []

    def incrby(self, key: str, amount: int):
        self._ops.append(("incrby", key, amount))
        return self

    def expire(self, key: str, seconds: int):
        self._ops.append(("expire", key, seconds))
        return self

    def incr(self, key: str):
        self._ops.append(("incr", key))
        return self

    def set(self, key: str, value, **kw):
        self._ops.append(("set", key, value))
        return self

    def get(self, key: str):
        self._ops.append(("get", key))
        return self

    async def execute(self):
        results = []
        for op in self._ops:
            if op[0] == "incrby":
                res = await self._redis.incrby(op[1], op[2])
                results.append(res)
            elif op[0] == "expire":
                res = await self._redis.expire(op[1], op[2])
                results.append(res)
            elif op[0] == "incr":
                res = await self._redis.incr(op[1])
                results.append(res)
            elif op[0] == "set":
                res = await self._redis.set(op[1], op[2])
                results.append(res)
            elif op[0] == "get":
                res = await self._redis.get(op[1])
                results.append(res)
        return results


# =====================================================================
#  Fixtures
# =====================================================================


@pytest.fixture
def fake_redis():
    """Return a fresh FakeRedis instance."""
    return FakeRedis()


@pytest.fixture
def patch_redis(fake_redis):
    """Patch get_redis to return our FakeRedis instance.

    We must patch in every module that does
    ``from backend.redis_client import get_redis`` because each gets its
    own local name binding.
    """

    async def _get_redis():
        return fake_redis

    with (
        patch("backend.redis_client.get_redis", new=_get_redis),
        patch("backend.services.circuit_breaker.get_redis", new=_get_redis),
        patch("backend.services.cache_metrics.get_redis", new=_get_redis),
        patch("backend.services.slo_metrics.get_redis", new=_get_redis),
        patch("backend.services.cost_tracker.get_redis", new=_get_redis),
    ):
        yield fake_redis


# =====================================================================
#  CircuitBreaker Tests
# =====================================================================


class TestCircuitBreaker:
    """Test circuit breaker state transitions with mocked Redis."""

    async def test_closed_allows_calls(self, patch_redis):
        """In CLOSED state, calls pass through successfully."""
        from backend.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker("test_service", failure_threshold=3)
        result = await cb.call(self._success_fn)
        assert result == "ok"

    async def test_closed_to_open_on_failures(self, patch_redis):
        """Circuit opens after reaching failure threshold."""
        from backend.services.circuit_breaker import CircuitBreaker, CircuitBreakerError

        cb = CircuitBreaker("test_fail", failure_threshold=3, recovery_timeout=60)

        # Trigger failures up to threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(self._failure_fn)

        # Next call should encounter OPEN circuit
        with pytest.raises(CircuitBreakerError) as exc:
            await cb.call(self._success_fn)
        assert "OPEN" in str(exc.value)

    async def test_open_rejects_calls(self, patch_redis, fake_redis):
        """OPEN circuit rejects all calls immediately."""
        from backend.services.circuit_breaker import (
            CircuitBreaker,
            CircuitBreakerError,
            CircuitState,
        )

        cb = CircuitBreaker("reject_test", failure_threshold=2)

        # Force circuit open via Redis state
        await fake_redis.set(cb._state_key, CircuitState.OPEN.value)
        await fake_redis.set(cb._opened_at_key, str(time.time()))

        with pytest.raises(CircuitBreakerError):
            await cb.call(self._success_fn)

    async def test_open_to_half_open_after_timeout(self, patch_redis, fake_redis):
        """Circuit transitions to HALF_OPEN after recovery timeout."""
        from backend.services.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("timeout_test", recovery_timeout=1)

        # Force OPEN with past timestamp
        await fake_redis.set(cb._state_key, CircuitState.OPEN.value)
        await fake_redis.set(cb._opened_at_key, str(time.time() - 10))

        # Should transition and execute
        result = await cb.call(self._success_fn)
        assert result == "ok"

        # Verify state is now HALF_OPEN (or CLOSED if success threshold == 1)
        state = await fake_redis.get(cb._state_key)
        assert state is not None

    async def test_half_open_to_closed_on_successes(self, patch_redis, fake_redis):
        """HALF_OPEN → CLOSED when enough successes recorded."""
        from backend.services.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("recovery_test", success_threshold=2, recovery_timeout=1)

        # Force HALF_OPEN
        await fake_redis.set(cb._state_key, CircuitState.HALF_OPEN.value)

        # First success: still HALF_OPEN
        await cb.call(self._success_fn)
        state = await fake_redis.get(cb._state_key)
        assert state.decode() == CircuitState.HALF_OPEN.value

        # Second success: should close
        await cb.call(self._success_fn)
        state = await fake_redis.get(cb._state_key)
        assert state.decode() == CircuitState.CLOSED.value

    async def test_half_open_to_open_on_failure(self, patch_redis, fake_redis):
        """HALF_OPEN → OPEN on any failure."""
        from backend.services.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("halfopen_fail", success_threshold=3)

        # Force HALF_OPEN
        await fake_redis.set(cb._state_key, CircuitState.HALF_OPEN.value)

        with pytest.raises(ValueError):
            await cb.call(self._failure_fn)

        state = await fake_redis.get(cb._state_key)
        assert state.decode() == CircuitState.OPEN.value

    async def test_get_status_closed(self, patch_redis):
        """get_status returns correct info for CLOSED state."""
        from backend.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker("status_test")
        status = await cb.get_status()
        assert status["name"] == "status_test"
        assert status["state"] == "closed"
        assert status["failures"] == 0

    async def test_get_status_open(self, patch_redis, fake_redis):
        """get_status returns retry_in_seconds when OPEN."""
        from backend.services.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("status_open", recovery_timeout=60)
        await fake_redis.set(cb._state_key, CircuitState.OPEN.value)
        await fake_redis.set(cb._opened_at_key, str(time.time()))

        status = await cb.get_status()
        assert status["state"] == "open"
        assert "retry_in_seconds" in status
        assert status["retry_in_seconds"] <= 60

    async def test_get_status_half_open(self, patch_redis, fake_redis):
        """get_status returns success info when HALF_OPEN."""
        from backend.services.circuit_breaker import CircuitBreaker, CircuitState

        cb = CircuitBreaker("status_half", success_threshold=3)
        await fake_redis.set(cb._state_key, CircuitState.HALF_OPEN.value)
        await fake_redis.set(cb._success_key, "1")

        status = await cb.get_status()
        assert status["state"] == "half_open"
        assert status["successes"] == 1
        assert status["success_threshold"] == 3

    async def test_success_resets_failure_counter(self, patch_redis, fake_redis):
        """A success in CLOSED state resets failure counter."""
        from backend.services.circuit_breaker import CircuitBreaker

        cb = CircuitBreaker("reset_test", failure_threshold=5)

        # Cause some failures
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(self._failure_fn)

        failures = int((await fake_redis.get(cb._failure_key)).decode())
        assert failures == 3

        # Success should reset
        await cb.call(self._success_fn)
        failures_after = await fake_redis.get(cb._failure_key)
        assert failures_after is None

    # --- Test helper functions ---

    @staticmethod
    async def _success_fn():
        return "ok"

    @staticmethod
    async def _failure_fn():
        raise ValueError("simulated failure")


# =====================================================================
#  CacheMetrics Tests
# =====================================================================


class TestCacheMetrics:
    """Test cache metrics with mocked Redis."""

    async def test_record_hit(self, patch_redis, fake_redis):
        """record_hit increments hit counter."""
        from backend.services.cache_metrics import CacheMetrics

        await CacheMetrics.record_hit("key1", "synthesis")

        # Verify counter was incremented
        today = time.strftime("%Y-%m-%d")
        key = f"cache_metrics:{today}:synthesis:hits"
        val = await fake_redis.get(key)
        assert int(val) == 1

    async def test_record_miss(self, patch_redis, fake_redis):
        """record_miss increments miss counter."""
        from backend.services.cache_metrics import CacheMetrics

        await CacheMetrics.record_miss("key2", "synthesis")

        today = time.strftime("%Y-%m-%d")
        key = f"cache_metrics:{today}:synthesis:misses"
        val = await fake_redis.get(key)
        assert int(val) == 1

    async def test_get_stats_empty(self, patch_redis):
        """get_stats returns zeros when no data."""
        from backend.services.cache_metrics import CacheMetrics

        stats = await CacheMetrics.get_stats("search")
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total"] == 0
        assert stats["hit_rate"] == 0.0

    async def test_get_stats_with_data(self, patch_redis):
        """get_stats calculates hit rate correctly."""
        from backend.services.cache_metrics import CacheMetrics

        # Record 7 hits and 3 misses
        for _ in range(7):
            await CacheMetrics.record_hit("k", "recommendations")
        for _ in range(3):
            await CacheMetrics.record_miss("k", "recommendations")

        stats = await CacheMetrics.get_stats("recommendations")
        assert stats["hits"] == 7
        assert stats["misses"] == 3
        assert stats["total"] == 10
        assert stats["hit_rate"] == 70.0

    async def test_get_all_stats(self, patch_redis):
        """get_all_stats returns stats for all operations."""
        from backend.services.cache_metrics import CacheMetrics

        # Add some data for synthesis
        await CacheMetrics.record_hit("k", "synthesis")

        all_stats = await CacheMetrics.get_all_stats()
        assert len(all_stats) == 3  # synthesis, search, recommendations
        ops = [s["operation"] for s in all_stats]
        assert "synthesis" in ops
        assert "search" in ops
        assert "recommendations" in ops


# =====================================================================
#  SLOMetrics Tests
# =====================================================================


class TestSLOMetrics:
    """Test SLO metrics with mocked Redis."""

    async def test_record_latency(self, patch_redis, fake_redis):
        """record_latency stores latency in sorted set."""
        from backend.services.slo_metrics import SLOMetrics

        await SLOMetrics.record_latency("search", 150)
        await SLOMetrics.record_latency("search", 200)
        await SLOMetrics.record_latency("search", 100)

        key = "slo:search:latencies"
        entries = await fake_redis.zrange(key, 0, -1, withscores=True)
        assert len(entries) == 3
        # Scores should be the latencies
        scores = sorted([s for _, s in entries])
        assert scores == [100, 150, 200]

    async def test_record_error(self, patch_redis, fake_redis):
        """record_error increments hourly error counter."""
        from backend.services.slo_metrics import SLOMetrics

        await SLOMetrics.record_error("synthesis")
        await SLOMetrics.record_error("synthesis")

        current_hour = time.strftime("%Y-%m-%d-%H")
        key = f"slo:synthesis:errors:{current_hour}"
        val = await fake_redis.get(key)
        assert int(val) == 2

    async def test_record_success(self, patch_redis, fake_redis):
        """record_success increments hourly success counter."""
        from backend.services.slo_metrics import SLOMetrics

        await SLOMetrics.record_success("search")

        current_hour = time.strftime("%Y-%m-%d-%H")
        key = f"slo:search:success:{current_hour}"
        val = await fake_redis.get(key)
        assert int(val) == 1

    async def test_get_stats_empty(self, patch_redis):
        """get_stats returns defaults when no data."""
        from backend.services.slo_metrics import SLOMetrics

        stats = await SLOMetrics.get_stats("search")
        assert stats["operation"] == "search"
        assert stats["samples"] == 0
        assert stats["meeting_slo"] is True

    async def test_get_stats_with_data(self, patch_redis):
        """get_stats calculates percentiles and SLO compliance."""
        from backend.services.slo_metrics import SLOMetrics

        # Record 20 latency measurements for "search" (target p95 < 5000)
        latencies = list(range(100, 2100, 100))  # 100, 200, ..., 2000
        for lat in latencies:
            await SLOMetrics.record_latency("search", lat)

        # Record some success/error counts
        for _ in range(8):
            await SLOMetrics.record_success("search")
        for _ in range(2):
            await SLOMetrics.record_error("search")

        stats = await SLOMetrics.get_stats("search")
        assert stats["samples"] == 20
        assert stats["p50_ms"] > 0
        assert stats["p95_ms"] > 0
        assert stats["meeting_slo"] is True  # All latencies < 5000ms

    async def test_get_stats_slo_violation(self, patch_redis):
        """get_stats detects SLO violation when p95 exceeds target."""
        from backend.services.slo_metrics import SLOMetrics

        # Record high latencies for "recommendation" (target p95 < 2000)
        for lat in range(3000, 6000, 100):  # 3000..5900 (all > 2000)
            await SLOMetrics.record_latency("recommendation", lat)

        stats = await SLOMetrics.get_stats("recommendation")
        assert stats["meeting_slo"] is False  # p95 exceeds 2000ms target

    async def test_get_all_stats(self, patch_redis):
        """get_all_stats returns stats for all defined operations."""
        from backend.services.slo_metrics import SLOMetrics

        all_stats = await SLOMetrics.get_all_stats()
        # SLO_TARGETS has 5 operations
        assert len(all_stats) == 5
        ops = [s["operation"] for s in all_stats]
        assert "search" in ops
        assert "synthesis" in ops


# =====================================================================
#  CostTracker Tests
# =====================================================================


class TestCostTracker:
    """Test cost tracking with mocked Redis and real DB."""

    async def test_track_usage_records_tokens(
        self, patch_redis, fake_redis, db_session
    ):
        """track_usage records token counts in Redis and DB."""
        from backend.services.cost_tracker import CostTracker

        user_id = uuid4()
        org_id = uuid4()

        tracker = CostTracker(db_session)
        result = await tracker.track_usage(
            user_id=user_id,
            org_id=org_id,
            operation="synthesis",
            model="gpt-4o",
            prompt_tokens=1000,
            completion_tokens=500,
        )

        assert result["tokens"] == 1500
        assert result["cost_usd"] > 0
        assert result["user_daily_total"] == 1500
        assert result["org_daily_total"] == 1500
        assert result["over_budget"] is False

    async def test_track_usage_accumulates(self, patch_redis, fake_redis, db_session):
        """Multiple track_usage calls accumulate correctly."""
        from backend.services.cost_tracker import CostTracker

        user_id = uuid4()
        org_id = uuid4()

        tracker = CostTracker(db_session)

        await tracker.track_usage(
            user_id=user_id,
            org_id=org_id,
            operation="chat",
            model="gpt-4o",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        result = await tracker.track_usage(
            user_id=user_id,
            org_id=org_id,
            operation="chat",
            model="gpt-4o",
            prompt_tokens=2000,
            completion_tokens=1000,
        )

        assert result["user_daily_total"] == 4500  # 1500 + 3000
        assert result["org_daily_total"] == 4500

    async def test_track_usage_cost_calculation(self, patch_redis, db_session):
        """Cost calculation uses correct pricing for models."""
        from backend.services.cost_tracker import CostTracker

        tracker = CostTracker(db_session)
        result = await tracker.track_usage(
            user_id=uuid4(),
            org_id=uuid4(),
            operation="embedding",
            model="text-embedding-3-small",
            prompt_tokens=1_000_000,
            completion_tokens=0,
        )

        # text-embedding-3-small: prompt=$0.02 per 1M
        assert result["cost_usd"] == pytest.approx(0.02, abs=0.001)

    async def test_check_budget_no_usage(self, patch_redis, db_session):
        """check_budget returns full budget when no usage."""
        from backend.services.cost_tracker import (
            DAILY_ORG_TOKEN_BUDGET,
            DAILY_USER_TOKEN_BUDGET,
            CostTracker,
        )

        tracker = CostTracker(db_session)
        budget = await tracker.check_budget(uuid4(), uuid4())

        assert budget["user_tokens"] == 0
        assert budget["org_tokens"] == 0
        assert budget["user_remaining"] == DAILY_USER_TOKEN_BUDGET
        assert budget["org_remaining"] == DAILY_ORG_TOKEN_BUDGET
        assert budget["over_budget"] is False

    async def test_check_budget_with_usage(self, patch_redis, fake_redis, db_session):
        """check_budget reflects accumulated usage."""
        from backend.services.cost_tracker import CostTracker

        user_id = uuid4()
        org_id = uuid4()

        tracker = CostTracker(db_session)
        await tracker.track_usage(
            user_id=user_id,
            org_id=org_id,
            operation="synthesis",
            model="gpt-4o",
            prompt_tokens=10000,
            completion_tokens=5000,
        )

        budget = await tracker.check_budget(user_id, org_id)
        assert budget["user_tokens"] == 15000
        assert budget["org_tokens"] == 15000
        assert budget["user_remaining"] == 50000 - 15000
        assert budget["over_budget"] is False

    async def test_over_budget_detection(self, patch_redis, fake_redis, db_session):
        """track_usage flags when over budget."""
        from backend.services.cost_tracker import DAILY_USER_TOKEN_BUDGET, CostTracker

        user_id = uuid4()
        org_id = uuid4()

        tracker = CostTracker(db_session)
        result = await tracker.track_usage(
            user_id=user_id,
            org_id=org_id,
            operation="synthesis",
            model="gpt-4o",
            prompt_tokens=DAILY_USER_TOKEN_BUDGET + 1,
            completion_tokens=0,
        )

        assert result["over_budget"] is True

    async def test_calculate_cost_gpt4o(self, patch_redis, db_session):
        """_calculate_cost for gpt-4o model."""
        from backend.services.cost_tracker import CostTracker

        # gpt-4o: prompt=$2.50/1M, completion=$10.00/1M
        cost = CostTracker._calculate_cost("gpt-4o", 1_000_000, 1_000_000)
        assert cost == pytest.approx(12.50, abs=0.01)

    async def test_calculate_cost_unknown_model(self, patch_redis, db_session):
        """_calculate_cost for unknown model returns 0."""
        from backend.services.cost_tracker import CostTracker

        cost = CostTracker._calculate_cost("unknown-model", 1000, 1000)
        assert cost == 0.0
