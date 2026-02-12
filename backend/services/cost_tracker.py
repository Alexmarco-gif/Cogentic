"""AI Cost Tracking Service - Token usage budgets and monitoring.

Tracks OpenAI token consumption per user/org with daily budgets.
Integrates with Redis for real-time counters and PostgreSQL for audit.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Column, DateTime, Float, Integer, String, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDMixin
from backend.redis_client import get_redis_client

logger = logging.getLogger(__name__)
redis_client = get_redis_client()

# Cost budgets (tokens per day)
DAILY_USER_TOKEN_BUDGET = 50_000  # ~$0.75/day per user at GPT-4o prices
DAILY_ORG_TOKEN_BUDGET = 500_000  # ~$7.50/day per org
ALERT_THRESHOLD = 0.80  # Alert at 80% budget


class AIUsageLog(Base, UUIDMixin, TimestampMixin):
    """AI token usage audit log."""

    __tablename__ = "ai_usage_logs"

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)  # synthesis, chat, brief_gen
    model: Mapped[str] = mapped_column(String(100), nullable=False)  # gpt-4o, text-embedding-3-small
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)


class CostTracker:
    """Track and enforce AI usage budgets."""

    # Model pricing (USD per 1M tokens) - GPT-4o as of Feb 2026
    PRICING = {
        "gpt-4o": {"prompt": 2.50, "completion": 10.00},
        "text-embedding-3-small": {"prompt": 0.02, "completion": 0.0},
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def track_usage(
        self,
        *,
        user_id: UUID,
        org_id: UUID,
        operation: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> dict[str, Any]:
        """Track AI token usage and check against budgets.

        Args:
            user_id: User UUID
            org_id: Org UUID
            operation: Operation type (synthesis, chat, brief_gen)
            model: Model name (gpt-4o, text-embedding-3-small)
            prompt_tokens: Prompt token count
            completion_tokens: Completion token count

        Returns:
            Usage summary with budget status
        """
        total_tokens = prompt_tokens + completion_tokens
        cost = self._calculate_cost(model, prompt_tokens, completion_tokens)

        # Increment Redis counters (today's usage)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        user_key = f"ai_usage:{today}:user:{user_id}"
        org_key = f"ai_usage:{today}:org:{org_id}"

        # Atomic increment with 25-hour TTL
        pipe = redis_client.pipeline()
        pipe.incrby(user_key, total_tokens)
        pipe.expire(user_key, 90000)  # 25 hours
        pipe.incrby(org_key, total_tokens)
        pipe.expire(org_key, 90000)
        user_total, _, org_total, _ = pipe.execute()

        # Log to database
        log = AIUsageLog(
            user_id=user_id,
            org_id=org_id,
            operation=operation,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
        )
        self.db.add(log)

        # Check budgets
        user_pct = (user_total / DAILY_USER_TOKEN_BUDGET) * 100
        org_pct = (org_total / DAILY_ORG_TOKEN_BUDGET) * 100

        if user_pct >= ALERT_THRESHOLD * 100:
            logger.warning(
                f"User {user_id} at {user_pct:.0f}% of daily token budget "
                f"({user_total}/{DAILY_USER_TOKEN_BUDGET})"
            )

        if org_pct >= ALERT_THRESHOLD * 100:
            logger.warning(
                f"Org {org_id} at {org_pct:.0f}% of daily token budget "
                f"({org_total}/{DAILY_ORG_TOKEN_BUDGET})"
            )

        return {
            "tokens": total_tokens,
            "cost_usd": round(cost, 6),
            "user_daily_total": user_total,
            "user_budget_pct": round(user_pct, 1),
            "org_daily_total": org_total,
            "org_budget_pct": round(org_pct, 1),
            "over_budget": user_total > DAILY_USER_TOKEN_BUDGET or org_total > DAILY_ORG_TOKEN_BUDGET,
        }

    async def check_budget(
        self,
        user_id: UUID,
        org_id: UUID,
    ) -> dict[str, Any]:
        """Check current budget status without logging usage."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        user_key = f"ai_usage:{today}:user:{user_id}"
        org_key = f"ai_usage:{today}:org:{org_id}"

        user_total = int(redis_client.get(user_key) or 0)
        org_total = int(redis_client.get(org_key) or 0)

        return {
            "user_tokens": user_total,
            "user_budget": DAILY_USER_TOKEN_BUDGET,
            "user_remaining": max(0, DAILY_USER_TOKEN_BUDGET - user_total),
            "org_tokens": org_total,
            "org_budget": DAILY_ORG_TOKEN_BUDGET,
            "org_remaining": max(0, DAILY_ORG_TOKEN_BUDGET - org_total),
            "over_budget": user_total > DAILY_USER_TOKEN_BUDGET or org_total > DAILY_ORG_TOKEN_BUDGET,
        }

    async def get_usage_summary(
        self,
        org_id: UUID,
        days: int = 7,
    ) -> dict[str, Any]:
        """Get usage summary for last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(AIUsageLog).where(
                AIUsageLog.org_id == org_id,
                AIUsageLog.created_at >= cutoff,
            )
        )
        logs = result.scalars().all()

        total_tokens = sum(log.total_tokens for log in logs)
        total_cost = sum(log.estimated_cost_usd for log in logs)

        by_operation = {}
        for log in logs:
            if log.operation not in by_operation:
                by_operation[log.operation] = {"tokens": 0, "cost": 0.0, "calls": 0}
            by_operation[log.operation]["tokens"] += log.total_tokens
            by_operation[log.operation]["cost"] += log.estimated_cost_usd
            by_operation[log.operation]["calls"] += 1

        return {
            "period_days": days,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 2),
            "by_operation": by_operation,
        }

    @classmethod
    def _calculate_cost(
        cls,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate cost in USD for token usage."""
        pricing = cls.PRICING.get(model, {"prompt": 0.0, "completion": 0.0})
        prompt_cost = (prompt_tokens / 1_000_000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * pricing["completion"]
        return prompt_cost + completion_cost
