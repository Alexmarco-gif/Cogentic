"""Circuit breaker for AI services.

Consolidated into backend.services.circuit_breaker.
This module re-exports for backward compatibility.
"""

from backend.services.circuit_breaker import (  # noqa: F401
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    openai_breaker,
)

# Backward-compatible factory
_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name)
    return _breakers[name]

