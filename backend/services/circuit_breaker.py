"""Circuit Breaker - Prevent cascading failures in AI services.

Implements the circuit breaker pattern for external API calls (OpenAI).
States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery).
"""

import logging
import time
from enum import Enum
from typing import Any, Callable

from backend.redis_client import get_redis

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(Exception):
    """Raised when circuit is OPEN."""

    pass


class CircuitBreaker:
    """Circuit breaker for AI/external services.

    Configuration:
        - failure_threshold: Failures before opening circuit (default: 5)
        - recovery_timeout: Seconds before trying recovery (default: 60)
        - success_threshold: Successes needed to close circuit (default: 2)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        # Redis keys
        self._state_key = f"circuit:{name}:state"
        self._failure_key = f"circuit:{name}:failures"
        self._success_key = f"circuit:{name}:successes"
        self._opened_at_key = f"circuit:{name}:opened_at"

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute.
            *args, **kwargs: Function arguments.

        Returns:
            Function result.

        Raises:
            CircuitBreakerError: If circuit is OPEN.
        """
        redis = await get_redis()
        state = await self._get_state(redis)

        if state == CircuitState.OPEN:
            # Check if recovery timeout elapsed
            opened_at = await redis.get(self._opened_at_key)
            if opened_at:
                elapsed = time.time() - float(opened_at)
                if elapsed >= self.recovery_timeout:
                    logger.info(
                        f"Circuit {self.name}: OPEN → HALF_OPEN (timeout elapsed)"
                    )
                    await self._set_state(redis, CircuitState.HALF_OPEN)
                    await redis.delete(self._success_key)
                else:
                    raise CircuitBreakerError(
                        f"Circuit {self.name} is OPEN. Retry in {int(self.recovery_timeout - elapsed)}s"
                    )
            else:
                raise CircuitBreakerError(f"Circuit {self.name} is OPEN")

        # Execute function
        try:
            result = await func(*args, **kwargs)
            await self._on_success(redis)
            return result
        except Exception:
            await self._on_failure(redis)
            raise

    async def _on_success(self, redis):
        """Handle successful call."""
        state = await self._get_state(redis)

        if state == CircuitState.HALF_OPEN:
            # Increment success counter
            successes = await redis.incr(self._success_key)
            if successes >= self.success_threshold:
                logger.info(
                    f"Circuit {self.name}: HALF_OPEN → CLOSED (recovery confirmed)"
                )
                await self._set_state(redis, CircuitState.CLOSED)
                await redis.delete(
                    self._failure_key, self._success_key, self._opened_at_key
                )
        elif state == CircuitState.CLOSED:
            # Reset failure counter on success
            await redis.delete(self._failure_key)

    async def _on_failure(self, redis):
        """Handle failed call."""
        state = await self._get_state(redis)

        if state == CircuitState.HALF_OPEN:
            # Immediate re-open on failure during recovery
            logger.warning(f"Circuit {self.name}: HALF_OPEN → OPEN (recovery failed)")
            await self._set_state(redis, CircuitState.OPEN)
            await redis.set(self._opened_at_key, time.time())
            await redis.delete(self._success_key)
        elif state == CircuitState.CLOSED:
            # Increment failure counter
            failures = await redis.incr(self._failure_key)
            await redis.expire(self._failure_key, 300)  # 5min rolling window

            if failures >= self.failure_threshold:
                logger.error(
                    f"Circuit {self.name}: CLOSED → OPEN "
                    f"({failures} failures exceed threshold {self.failure_threshold})"
                )
                await self._set_state(redis, CircuitState.OPEN)
                await redis.set(self._opened_at_key, time.time())

    async def _get_state(self, redis) -> CircuitState:
        """Get current circuit state."""
        state_str = await redis.get(self._state_key)
        if not state_str:
            return CircuitState.CLOSED
        return CircuitState(
            state_str.decode() if isinstance(state_str, bytes) else state_str
        )

    async def _set_state(self, redis, state: CircuitState):
        """Set circuit state."""
        await redis.set(self._state_key, state.value)

    async def get_status(self) -> dict[str, Any]:
        """Get circuit breaker status."""
        redis = await get_redis()
        state = await self._get_state(redis)
        failures = int(await redis.get(self._failure_key) or 0)
        successes = int(await redis.get(self._success_key) or 0)
        opened_at = await redis.get(self._opened_at_key)

        status = {
            "name": self.name,
            "state": state.value,
            "failures": failures,
            "failure_threshold": self.failure_threshold,
        }

        if state == CircuitState.OPEN and opened_at:
            elapsed = time.time() - float(opened_at)
            status["retry_in_seconds"] = max(0, int(self.recovery_timeout - elapsed))

        if state == CircuitState.HALF_OPEN:
            status["successes"] = successes
            status["success_threshold"] = self.success_threshold

        return status


# Pre-configured breakers for AI services
openai_breaker = CircuitBreaker(
    name="openai",
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=2,
)
