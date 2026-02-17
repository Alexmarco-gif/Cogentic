"""Cost tracking middleware for AI usage.

Tracks token usage and costs per user/org/endpoint to enable:
  - Real-time budget alerts
  - Cost attribution and chargebacks
  - Anomaly detection
  - Cost optimization decisions
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from backend.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# OpenAI pricing (as of Feb 2026)
# GPT-4o: $5/1M input, $15/1M output
# text-embedding-3-small: $0.02/1M tokens
PRICING = {
    "gpt-4o": {"input": 5.0 / 1_000_000, "output": 15.0 / 1_000_000},
    "text-embedding-3-small": {"input": 0.02 / 1_000_000, "output": 0.0},
}


class CostTracker:
    """Tracks and enforces AI usage costs per user/org.

    Budget enforcement:
      - Per-user daily limit: $5
      - Per-org daily limit: $100
      - Per-org monthly limit: $2000

    Redis keys:
      - cost:user:{user_id}:daily → float (USD)
      - cost:org:{org_id}:daily → float (USD)
      - cost:org:{org_id}:monthly → float (USD)
      - cost:metrics:{YYYY-MM-DD} → hash (endpoint → total_cost)
    """

    def __init__(self):
        self.redis = get_redis_client()

    def track_tokens(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        user_id: UUID | None = None,
        org_id: UUID | None = None,
        endpoint: str | None = None,
    ) -> dict[str, Any]:
        """Track token usage and calculate cost.

        Args:
            model: Model name (gpt-4o, text-embedding-3-small)
            input_tokens: Input token count
            output_tokens: Output token count
            user_id: User UUID
            org_id: Org UUID
            endpoint: API endpoint for metrics

        Returns:
            Dict with cost, warning flags, and limits info
        """
        # Calculate cost
        pricing = PRICING.get(model, {"input": 0.0, "output": 0.0})
        input_cost = input_tokens * pricing["input"]
        output_cost = output_tokens * pricing["output"]
        total_cost = input_cost + output_cost

        # Update Redis counters
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        month = datetime.now(timezone.utc).strftime("%Y-%m")

        if user_id:
            user_key = f"cost:user:{user_id}:daily"
            user_cost = self._increment_cost(user_key, total_cost, ttl=86400)
        else:
            user_cost = 0.0

        if org_id:
            org_daily_key = f"cost:org:{org_id}:daily"
            org_monthly_key = f"cost:org:{org_id}:monthly:{month}"
            org_daily_cost = self._increment_cost(org_daily_key, total_cost, ttl=86400)
            org_monthly_cost = self._increment_cost(
                org_monthly_key, total_cost, ttl=2678400
            )  # 31 days
        else:
            org_daily_cost = 0.0
            org_monthly_cost = 0.0

        # Track per-endpoint metrics
        if endpoint:
            metrics_key = f"cost:metrics:{today}"
            self.redis.hincrbyfloat(metrics_key, endpoint, total_cost)
            self.redis.expire(metrics_key, 2678400)  # 31 days

        # Check limits
        warnings = []
        user_limit_pct = (user_cost / 5.0) * 100 if user_id else 0
        org_daily_limit_pct = (org_daily_cost / 100.0) * 100 if org_id else 0
        org_monthly_limit_pct = (org_monthly_cost / 2000.0) * 100 if org_id else 0

        if user_limit_pct > 80:
            warnings.append(f"User daily limit: {user_limit_pct:.1f}% used")
        if org_daily_limit_pct > 80:
            warnings.append(f"Org daily limit: {org_daily_limit_pct:.1f}% used")
        if org_monthly_limit_pct > 80:
            warnings.append(f"Org monthly limit: {org_monthly_limit_pct:.1f}% used")

        return {
            "cost_usd": round(total_cost, 6),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "user_daily_cost": round(user_cost, 4),
            "user_daily_limit_pct": round(user_limit_pct, 1),
            "org_daily_cost": round(org_daily_cost, 4),
            "org_daily_limit_pct": round(org_daily_limit_pct, 1),
            "org_monthly_cost": round(org_monthly_cost, 4),
            "org_monthly_limit_pct": round(org_monthly_limit_pct, 1),
            "warnings": warnings,
        }

    def check_budget(
        self,
        *,
        user_id: UUID | None = None,
        org_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Check current budget usage without tracking new usage.

        Returns:
            Dict with current usage and whether limits are exceeded
        """
        month = datetime.now(timezone.utc).strftime("%Y-%m")

        user_cost = 0.0
        if user_id:
            user_key = f"cost:user:{user_id}:daily"
            user_cost = float(self.redis.get(user_key) or 0.0)

        org_daily_cost = 0.0
        org_monthly_cost = 0.0
        if org_id:
            org_daily_key = f"cost:org:{org_id}:daily"
            org_monthly_key = f"cost:org:{org_id}:monthly:{month}"
            org_daily_cost = float(self.redis.get(org_daily_key) or 0.0)
            org_monthly_cost = float(self.redis.get(org_monthly_key) or 0.0)

        # Check if any limit is exceeded
        user_exceeded = user_cost >= 5.0
        org_daily_exceeded = org_daily_cost >= 100.0
        org_monthly_exceeded = org_monthly_cost >= 2000.0

        return {
            "user_daily_cost": round(user_cost, 4),
            "user_daily_limit": 5.0,
            "user_exceeded": user_exceeded,
            "org_daily_cost": round(org_daily_cost, 4),
            "org_daily_limit": 100.0,
            "org_daily_exceeded": org_daily_exceeded,
            "org_monthly_cost": round(org_monthly_cost, 4),
            "org_monthly_limit": 2000.0,
            "org_monthly_exceeded": org_monthly_exceeded,
            "budget_ok": not (
                user_exceeded or org_daily_exceeded or org_monthly_exceeded
            ),
        }

    def get_endpoint_metrics(
        self,
        *,
        date: str | None = None,
    ) -> dict[str, float]:
        """Get cost breakdown by endpoint for a given date.

        Args:
            date: YYYY-MM-DD format (defaults to today)

        Returns:
            Dict of endpoint -> total_cost_usd
        """
        if not date:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        metrics_key = f"cost:metrics:{date}"
        raw = self.redis.hgetall(metrics_key)

        return {endpoint.decode(): float(cost) for endpoint, cost in raw.items()}

    def _increment_cost(self, key: str, amount: float, ttl: int) -> float:
        """Atomically increment cost counter with TTL."""
        pipe = self.redis.pipeline()
        pipe.incrbyfloat(key, amount)
        pipe.expire(key, ttl)
        result = pipe.execute()
        return float(result[0])


# Singleton
_tracker: CostTracker | None = None


def get_cost_tracker() -> CostTracker:
    """Get or create the cost tracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker
