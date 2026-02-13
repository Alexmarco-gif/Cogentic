"""SLO Metrics - Service Level Objective tracking and monitoring.

Tracks response times, error rates, and availability per endpoint.
"""

import logging
import time
from typing import Any

from backend.redis_client import get_redis_client

logger = logging.getLogger(__name__)
redis_client = get_redis_client()

# SLO Targets (percentile response times in milliseconds)
SLO_TARGETS = {
    "search": {"p95": 5000, "p99": 8000},  # Deep search target: p95 < 5s
    "synthesis": {"p95": 3000, "p99": 5000},  # RAG synthesis target: p95 < 3s
    "brief_generation": {"p95": 10000, "p99": 15000},  # Brief gen target: p95 < 10s
    "brief_refresh": {"p95": 8000, "p99": 12000},  # Brief refresh target: p95 < 8s
    "recommendation": {"p95": 2000, "p99": 4000},  # Recommendations target: p95 < 2s
}


class SLOMetrics:
    """Track SLO compliance for critical operations."""

    @staticmethod
    def record_latency(operation: str, duration_ms: int):
        """Record operation latency."""
        # Store in sorted set (score = timestamp, value = duration)
        timestamp = time.time()
        key = f"slo:{operation}:latencies"
        redis_client.zadd(key, {str(duration_ms): timestamp})

        # Keep last 1000 measurements
        redis_client.zremrangebyrank(key, 0, -1001)
        redis_client.expire(key, 3600)  # 1 hour

    @staticmethod
    def record_error(operation: str):
        """Record operation error."""
        today = time.strftime("%Y-%m-%d-%H")  # Hourly buckets
        key = f"slo:{operation}:errors:{today}"
        redis_client.incr(key)
        redis_client.expire(key, 86400)  # 24 hours

    @staticmethod
    def record_success(operation: str):
        """Record successful operation."""
        today = time.strftime("%Y-%m-%d-%H")
        key = f"slo:{operation}:success:{today}"
        redis_client.incr(key)
        redis_client.expire(key, 86400)

    @staticmethod
    def get_stats(operation: str) -> dict[str, Any]:
        """Get SLO statistics for an operation."""
        # Get latencies
        key = f"slo:{operation}:latencies"
        latencies = redis_client.zrange(key, 0, -1)
        latencies = [
            int(l) if isinstance(l, bytes) else int(l.decode()) for l in latencies
        ]

        if not latencies:
            return {
                "operation": operation,
                "samples": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0,
                "slo_target_p95": SLO_TARGETS.get(operation, {}).get("p95", 0),
                "meeting_slo": True,
            }

        # Calculate percentiles
        latencies.sort()
        n = len(latencies)
        p50 = latencies[int(n * 0.50)]
        p95 = latencies[int(n * 0.95)]
        p99 = latencies[int(n * 0.99)] if n > 10 else latencies[-1]

        # Check SLO compliance
        target = SLO_TARGETS.get(operation, {})
        meeting_slo = p95 <= target.get("p95", float("inf"))

        # Get error rate (last hour)
        current_hour = time.strftime("%Y-%m-%d-%H")
        errors = int(redis_client.get(f"slo:{operation}:errors:{current_hour}") or 0)
        successes = int(
            redis_client.get(f"slo:{operation}:success:{current_hour}") or 0
        )
        total = errors + successes
        error_rate = (errors / total * 100) if total > 0 else 0

        return {
            "operation": operation,
            "samples": n,
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "slo_target_p95_ms": target.get("p95", 0),
            "slo_target_p99_ms": target.get("p99", 0),
            "meeting_slo": meeting_slo,
            "error_rate_pct": round(error_rate, 2),
            "errors_last_hour": errors,
            "successes_last_hour": successes,
        }

    @staticmethod
    def get_all_stats() -> list[dict[str, Any]]:
        """Get SLO stats for all operations."""
        return [SLOMetrics.get_stats(op) for op in SLO_TARGETS]
