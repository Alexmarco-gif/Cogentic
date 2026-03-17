"""AI Chat Agent module.

Conversational AI layer providing natural language signal interaction
with tool orchestration, SSE streaming, and industry-specific prompts.

Components:
  - agent.py:   Core LLM reasoning loop with tool orchestration
  - tools.py:   Tool definitions (search_signals, deep_search, etc.)
  - context.py: Conversation context manager (Redis-backed)
  - prompts.py: Industry-specific system prompts
"""

from backend.agent.agent import ChatAgent, SSEEvent
from backend.agent.context import ConversationContext
from backend.agent.prompts import get_system_prompt
from backend.agent.tools import TOOL_SCHEMAS, execute_tool

__all__ = [
    "ChatAgent",
    "SSEEvent",
    "ConversationContext",
    "get_system_prompt",
    "TOOL_SCHEMAS",
    "execute_tool",
]
