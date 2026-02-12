"""Circuit breaker for AI services.

Prevents cascading failures when OpenAI API is degraded or rate-limited.
Uses sliding window of failures to trip the breaker.

States:
  - CLOSED: Normal operation
  - OPEN: Failing fast (no API calls)
  - HALF_OPEN: Test recovery with limited requests
"""

import logging
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from fastapi import HTTPException

from backend.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5  # Failures to trip breaker
    success_threshold: int = 2  # Successes to close from half-open
    timeout_seconds: int = 60  # How long to stay open
    window_seconds: int = 60  # Sliding window for failure tracking


class CircuitBreaker:
    """Circuit breaker for AI API calls.

    Uses Redis for distributed state across multiple workers/containers.
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.redis = get_redis_client()

        self._state_key = f"circuit:{name}:state"
        self._failures_key = f"circuit:{name}:failures"
        self._successes_key = f"circuit:{name}:successes"
        self._opened_at_key = f"circuit:{name}:opened_at"

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        raw = self.redis.get(self._state_key)
        if not raw:
            return CircuitState.CLOSED
        return CircuitState(raw.decode())

    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result

        Raises:
            HTTPException 503: If circuit is open
        """
        current_state = self.state

        if current_state == CircuitState.OPEN:
            # Check if timeout has elapsed
            opened_at = self.redis.get(self._opened_at_key)
            if opened_at:
                elapsed = time.time() - float(opened_at)
                if elapsed >= self.config.timeout_seconds:
                    # Transition to half-open
                    self._transition_to_half_open()
                    current_state = CircuitState.HALF_OPEN
                else:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Service temporarily unavailable (circuit open for {int(elapsed)}s)",
                    )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Record successful call."""
        current_state = self.state

        if current_state == CircuitState.HALF_OPEN:
            # Increment success counter
            successes = self.redis.incr(self._successes_key)
            if successes >= self.config.success_threshold:
                self._transition_to_closed()
        elif current_state == CircuitState.CLOSED:
            # Reset failure counter on success
            self.redis.delete(self._failures_key)

    def _on_failure(self):
        """Record failed call."""
        current_state = self.state

        if current_state == CircuitState.HALF_OPEN:
            # Immediate trip back to open
            self._transition_to_open()
        elif current_state == CircuitState.CLOSED:
            # Increment failure counter with expiry
            pipe = self.redis.pipeline()
            pipe.incr(self._failures_key)
            pipe.expire(self._failures_key, self.config.window_seconds)
            failures = pipe.execute()[0]

            if failures >= self.config.failure_threshold:
                self._transition_to_open()

    def _transition_to_closed(self):
        """Transition to CLOSED state (normal operation)."""
        logger.info(f"Circuit breaker [{self.name}]: CLOSED")
        pipe = self.redis.pipeline()
        pipe.set(self._state_key, CircuitState.CLOSED.value)
        pipe.delete(self._failures_key)
        pipe.delete(self._successes_key)
        pipe.delete(self._opened_at_key)
        pipe.execute()

    def _transition_to_open(self):
        """Transition to OPEN state (failing fast)."""
        logger.warning(f"Circuit breaker [{self.name}]: OPEN (failing fast)")
        pipe = self.redis.pipeline()
        pipe.set(self._state_key, CircuitState.OPEN.value)
        pipe.set(self._opened_at_key, time.time())
        pipe.delete(self._failures_key)
        pipe.delete(self._successes_key)
        pipe.execute()

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state (testing recovery)."""
        logger.info(f"Circuit breaker [{self.name}]: HALF_OPEN (testing recovery)")
        pipe = self.redis.pipeline()
        pipe.set(self._state_key, CircuitState.HALF_OPEN.value)
        pipe.delete(self._successes_key)
        pipe.delete(self._opened_at_key)
        pipe.execute()

    def reset(self):
        """Manually reset circuit to CLOSED (admin action)."""
        self._transition_to_closed()


# Singleton circuit breakers for each AI model
_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name)
    return _breakers[name]
