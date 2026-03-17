"""AI Chat Agent with function-calling.

Session-based conversational interface with memory (last 10 messages).
Supports function-calling to search signals, pull briefs, query entities.
Streams responses via SSE.

Implementation lives in backend.agent module. This file re-exports
for backward compatibility.
"""

from backend.agent.agent import ChatAgent, SSEEvent  # noqa: F401
from backend.agent.context import ConversationContext  # noqa: F401
from backend.agent.prompts import get_system_prompt  # noqa: F401
from backend.agent.tools import TOOL_SCHEMAS, execute_tool  # noqa: F401
from backend.services.chat_agent_service import ChatAgentService  # noqa: F401

__all__ = [
    "ChatAgent",
    "SSEEvent",
    "ConversationContext",
    "get_system_prompt",
    "TOOL_SCHEMAS",
    "execute_tool",
    "ChatAgentService",
]
