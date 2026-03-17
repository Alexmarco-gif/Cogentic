"""Model Fallback Strategy - Cost optimization for AI operations.

Consolidated into backend.ai.model_router.ModelRouter.
This module re-exports for backward compatibility.
"""

from backend.ai.model_router import (  # noqa: F401
    ModelRouter,
    ModelTier,
    TaskType,
    get_model_router,
)

# Default embedding model (no fallback, always use this)
EMBEDDING_MODEL = "text-embedding-3-small"


class ModelSelector:
    """Deprecated: Use ModelRouter.get_model_for_task() instead.

    Kept for backward compatibility — delegates to ModelRouter.
    """

    @staticmethod
    def select_for_synthesis(query_length: int, context_length: int) -> str:
        router = get_model_router()
        return router.get_model_for_task(
            TaskType.RAG_SYNTHESIS,
            query_length=query_length,
            context_length=context_length,
        )

    @staticmethod
    def select_for_brief(signal_count: int) -> str:
        router = get_model_router()
        return router.get_model_for_task(
            TaskType.BRIEF_GENERATION,
            signal_count=signal_count,
        )

    @staticmethod
    def select_for_chat(message_history_length: int) -> str:
        router = get_model_router()
        return router.get_model_for_task(
            TaskType.CHAT_RESPONSE,
            message_history_length=message_history_length,
        )

    @staticmethod
    def get_model_config(model_name: str) -> dict:
        return ModelRouter.get_model_config(model_name)
