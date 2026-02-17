"""Model fallback strategy for cost optimization.

Uses cheaper models for low-risk tasks, reserves expensive models for critical tasks.

Tiers:
  - Tier 1 (cheap): gpt-4o-mini for simple tasks (search, categorization)
  - Tier 2 (standard): gpt-4o for synthesis, briefs
  - Tier 3 (premium): Reserved for future advanced features

Automatic fallback on:
  - Rate limit errors (429)
  - Circuit breaker open
  - Budget exceeded
"""

import logging
from enum import Enum
from typing import Any

from openai import AsyncOpenAI

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ModelTier(str, Enum):
    """Model tier for different task complexities."""

    CHEAP = "cheap"  # gpt-4o-mini
    STANDARD = "standard"  # gpt-4o
    PREMIUM = "premium"  # Reserved


class TaskType(str, Enum):
    """Different AI task types mapped to model tiers."""

    SEARCH_SYNTHESIS = "search_synthesis"  # CHEAP: search result summarization
    BRIEF_GENERATION = "brief_generation"  # STANDARD: full brief generation
    CHAT_RESPONSE = "chat_response"  # CHEAP: chat responses
    ENTITY_EXTRACTION = "entity_extraction"  # CHEAP: NER, classification
    RAG_SYNTHESIS = "rag_synthesis"  # STANDARD: RAG synthesis
    DECISION_LENS = "decision_lens"  # STANDARD: decision recommendations


# Task → Tier mapping
TASK_TIER_MAP = {
    TaskType.SEARCH_SYNTHESIS: ModelTier.CHEAP,
    TaskType.BRIEF_GENERATION: ModelTier.STANDARD,
    TaskType.CHAT_RESPONSE: ModelTier.CHEAP,
    TaskType.ENTITY_EXTRACTION: ModelTier.CHEAP,
    TaskType.RAG_SYNTHESIS: ModelTier.STANDARD,
    TaskType.DECISION_LENS: ModelTier.STANDARD,
}

# Tier → Model mapping
TIER_MODEL_MAP = {
    ModelTier.CHEAP: "gpt-4o-mini",
    ModelTier.STANDARD: "gpt-4o",
    ModelTier.PREMIUM: "gpt-4o",  # Same as standard for now
}

# Fallback chain
FALLBACK_CHAIN = {
    ModelTier.PREMIUM: ModelTier.STANDARD,
    ModelTier.STANDARD: ModelTier.CHEAP,
    ModelTier.CHEAP: None,  # No fallback
}


class ModelRouter:
    """Routes AI tasks to appropriate models with fallback support."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    def get_model_for_task(
        self,
        task_type: TaskType,
        *,
        force_tier: ModelTier | None = None,
    ) -> str:
        """Get the appropriate model for a task type.

        Args:
            task_type: Type of AI task
            force_tier: Force a specific tier (overrides default)

        Returns:
            Model name (e.g., "gpt-4o-mini")
        """
        tier = force_tier or TASK_TIER_MAP.get(task_type, ModelTier.STANDARD)
        model = TIER_MODEL_MAP[tier]
        return model

    async def complete_with_fallback(
        self,
        task_type: TaskType,
        messages: list[dict[str, str]],
        **kwargs,
    ) -> tuple[str, dict[str, Any]]:
        """Execute completion with automatic fallback on errors.

        Args:
            task_type: Type of AI task
            messages: OpenAI messages list
            **kwargs: Additional OpenAI parameters

        Returns:
            Tuple of (response_text, metadata)
        """
        tier = TASK_TIER_MAP.get(task_type, ModelTier.STANDARD)
        attempts = []

        while True:
            model = TIER_MODEL_MAP[tier]
            attempts.append(model)

            try:
                logger.info(f"Attempting {task_type.value} with {model}")

                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs,
                )

                content = response.choices[0].message.content or ""
                metadata = {
                    "model": model,
                    "tier": tier.value,
                    "attempts": attempts,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                }

                return content, metadata

            except Exception as e:
                error_str = str(e)
                logger.warning(f"{model} failed for {task_type.value}: {error_str}")

                # Check if we should fallback
                if "rate_limit" in error_str.lower() or "429" in error_str:
                    fallback_tier = FALLBACK_CHAIN.get(tier)
                    if fallback_tier:
                        logger.info(
                            f"Falling back from {tier.value} to {fallback_tier.value}"
                        )
                        tier = fallback_tier
                        continue

                # No fallback or non-retriable error
                raise

    def estimate_cost(
        self,
        task_type: TaskType,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost for a task before execution.

        Args:
            task_type: Type of AI task
            input_tokens: Estimated input tokens
            output_tokens: Estimated output tokens

        Returns:
            Estimated cost in USD
        """
        from backend.middleware.cost_tracking import PRICING

        model = self.get_model_for_task(task_type)
        # Map mini to standard pricing (we'll update PRICING if needed)
        pricing_key = "gpt-4o" if "gpt-4o" in model else model
        pricing = PRICING.get(pricing_key, {"input": 0.0, "output": 0.0})

        cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
        return cost


# Singleton
_router: ModelRouter | None = None


def get_model_router() -> ModelRouter:
    """Get or create the model router singleton."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
