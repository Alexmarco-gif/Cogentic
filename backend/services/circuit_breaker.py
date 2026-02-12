"""Circuit Breaker - Prevent cascading failures in AI services.

Implements the circuit breaker pattern for external API calls (OpenAI).
States: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery).
"""

import logging
import time
from enum import Enum
from typing import Any, Callable

from backend.redis_client import get_redis_client

logger = logging.getLogger(__name__)
redis_client = get_redis_client()


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

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute.
            *args, **kwargs: Function arguments.

        Returns:
            Function result.

        Raises:
            CircuitBreakerError: If circuit is OPEN.
        """
        state = self._get_state()

        if state == CircuitState.OPEN:
            # Check if recovery timeout elapsed
            opened_at = redis_client.get(self._opened_at_key)
            if opened_at:
                elapsed = time.time() - float(opened_at)
                if elapsed >= self.recovery_timeout:
                    logger.info(f"Circuit {self.name}: OPEN → HALF_OPEN (timeout elapsed)")
                    self._set_state(CircuitState.HALF_OPEN)
                    redis_client.delete(self._success_key)
                else:
                    raise CircuitBreakerError(
                        f"Circuit {self.name} is OPEN. Retry in {int(self.recovery_timeout - elapsed)}s"
                    )
            else:
                raise CircuitBreakerError(f"Circuit {self.name} is OPEN")

        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        state = self._get_state()

        if state == CircuitState.HALF_OPEN:
            # Increment success counter
            successes = redis_client.incr(self._success_key)
            if successes >= self.success_threshold:
                logger.info(f"Circuit {self.name}: HALF_OPEN → CLOSED (recovery confirmed)")
                self._set_state(CircuitState.CLOSED)
                redis_client.delete(self._failure_key, self._success_key, self._opened_at_key)
        elif state == CircuitState.CLOSED:
            # Reset failure counter on success
            redis_client.delete(self._failure_key)

    def _on_failure(self):
        """Handle failed call."""
        state = self._get_state()

        if state == CircuitState.HALF_OPEN:
            # Immediate re-open on failure during recovery
            logger.warning(f"Circuit {self.name}: HALF_OPEN → OPEN (recovery failed)")
            self._set_state(CircuitState.OPEN)
            redis_client.set(self._opened_at_key, time.time())
            redis_client.delete(self._success_key)
        elif state == CircuitState.CLOSED:
            # Increment failure counter
            failures = redis_client.incr(self._failure_key)
            redis_client.expire(self._failure_key, 300)  # 5min rolling window

            if failures >= self.failure_threshold:
                logger.error(
                    f"Circuit {self.name}: CLOSED → OPEN "
                    f"({failures} failures exceed threshold {self.failure_threshold})"
                )
                self._set_state(CircuitState.OPEN)
                redis_client.set(self._opened_at_key, time.time())

    def _get_state(self) -> CircuitState:
        """Get current circuit state."""
        state_str = redis_client.get(self._state_key)
        if not state_str:
            return CircuitState.CLOSED
        return CircuitState(state_str.decode() if isinstance(state_str, bytes) else state_str)

    def _set_state(self, state: CircuitState):
        """Set circuit state."""
        redis_client.set(self._state_key, state.value)

    def get_status(self) -> dict[str, Any]:
        """Get circuit breaker status."""
        state = self._get_state()
        failures = int(redis_client.get(self._failure_key) or 0)
        successes = int(redis_client.get(self._success_key) or 0)
        opened_at = redis_client.get(self._opened_at_key)

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
