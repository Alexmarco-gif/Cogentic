"""Model Fallback Strategy - Cost optimization for AI operations.

Routes operations to cheaper models when appropriate:
- Simple synthesis → gpt-4o-mini
- Complex synthesis → gpt-4o
- Embeddings → text-embedding-3-small (fixed)
"""

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ModelTier(str, Enum):
    """Model tier for cost optimization."""

    FAST = "fast"  # Cheapest, fastest (gpt-4o-mini)
    STANDARD = "standard"  # Balanced (gpt-4o)
    PREMIUM = "premium"  # Best quality (future: gpt-4-turbo)


class ModelSelector:
    """Select appropriate model based on operation complexity."""

    # Model configuration
    MODELS = {
        ModelTier.FAST: {
            "name": "gpt-4o-mini",
            "max_tokens": 16000,
            "cost_per_1m_prompt": 0.15,
            "cost_per_1m_completion": 0.60,
        },
        ModelTier.STANDARD: {
            "name": "gpt-4o",
            "max_tokens": 128000,
            "cost_per_1m_prompt": 2.50,
            "cost_per_1m_completion": 10.00,
        },
    }

    @staticmethod
    def select_for_synthesis(query_length: int, context_length: int) -> str:
        """Select model for RAG synthesis.

        Args:
            query_length: Query string length
            context_length: Total context length (retrieved signals)

        Returns:
            Model name
        """
        # Use fast model for simple queries with small context
        if query_length < 100 and context_length < 2000:
            logger.debug("Using gpt-4o-mini for simple synthesis")
            return ModelSelector.MODELS[ModelTier.FAST]["name"]

        # Use standard model for complex queries
        logger.debug("Using gpt-4o for complex synthesis")
        return ModelSelector.MODELS[ModelTier.STANDARD]["name"]

    @staticmethod
    def select_for_brief(signal_count: int) -> str:
        """Select model for brief generation.

        Args:
            signal_count: Number of signals to synthesize

        Returns:
            Model name
        """
        # Always use standard model for briefs (quality critical)
        return ModelSelector.MODELS[ModelTier.STANDARD]["name"]

    @staticmethod
    def select_for_chat(message_history_length: int) -> str:
        """Select model for chat.

        Args:
            message_history_length: Length of chat history

        Returns:
            Model name
        """
        # Use fast model for short conversations
        if message_history_length < 5:
            return ModelSelector.MODELS[ModelTier.FAST]["name"]

        # Standard model for longer conversations
        return ModelSelector.MODELS[ModelTier.STANDARD]["name"]

    @staticmethod
    def get_model_config(model_name: str) -> dict[str, Any]:
        """Get model configuration."""
        for tier, config in ModelSelector.MODELS.items():
            if config["name"] == model_name:
                return config
        return ModelSelector.MODELS[ModelTier.STANDARD]


# Default embedding model (no fallback, always use this)
EMBEDDING_MODEL = "text-embedding-3-small"
