"""Conversation context manager for the AI Chat Agent.

Manages short-term memory via Redis for active chat sessions.
Provides context window management (last 10 messages as per spec).

Architecture:
  - Redis key: chat:context:{session_id}
  - TTL: 30 minutes (refreshed on each interaction)
  - Stores: last 10 messages + session metadata
  - Falls back to DB if Redis miss
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from backend.redis_client import get_redis

logger = logging.getLogger(__name__)

# Context configuration
CONTEXT_TTL_SECONDS = 1800  # 30 minutes
MAX_CONTEXT_MESSAGES = 10
CONTEXT_KEY_PREFIX = "chat:context"


class ConversationContext:
    """Manages conversation context in Redis for fast retrieval.

    The context window is the last 10 messages (per WP-0.2 spec).
    Context is cached in Redis for the duration of the active session,
    and falls back to the DB ChatSessionRepository if cache misses.
    """

    @staticmethod
    def _key(session_id: UUID) -> str:
        """Generate Redis key for a session context."""
        return f"{CONTEXT_KEY_PREFIX}:{session_id}"

    async def load(self, session_id: UUID) -> dict[str, Any] | None:
        """Load conversation context from Redis.

        Returns:
            Context dict with 'messages' and 'metadata', or None if not cached.
        """
        redis = await get_redis()
        key = self._key(session_id)

        data = await redis.get(key)
        if not data:
            return None

        try:
            context = json.loads(data)
            # Refresh TTL on access
            await redis.expire(key, CONTEXT_TTL_SECONDS)
            return context
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Invalid context data for session {session_id}")
            await redis.delete(key)
            return None

    async def save(
        self,
        session_id: UUID,
        messages: list[dict[str, str]],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Save conversation context to Redis.

        Only keeps the last MAX_CONTEXT_MESSAGES messages.

        Args:
            session_id: Chat session ID.
            messages: List of message dicts with 'role' and 'content'.
            metadata: Optional session metadata (industry, signal refs, etc.)
        """
        redis = await get_redis()
        key = self._key(session_id)

        # Trim to context window
        trimmed = messages[-MAX_CONTEXT_MESSAGES:]

        context = {
            "session_id": str(session_id),
            "messages": trimmed,
            "metadata": metadata or {},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        await redis.set(key, json.dumps(context), ex=CONTEXT_TTL_SECONDS)

    async def append_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
    ) -> list[dict[str, str]]:
        """Append a message to the context and return updated messages list.

        Maintains the context window at MAX_CONTEXT_MESSAGES.

        Args:
            session_id: Chat session ID.
            role: Message role ('user', 'assistant', 'system').
            content: Message content.

        Returns:
            Updated messages list.
        """
        context = await self.load(session_id)

        if context:
            messages = context.get("messages", [])
            metadata = context.get("metadata", {})
        else:
            messages = []
            metadata = {}

        messages.append({"role": role, "content": content})

        # Trim context window
        messages = messages[-MAX_CONTEXT_MESSAGES:]

        await self.save(session_id, messages, metadata)
        return messages

    async def set_metadata(
        self,
        session_id: UUID,
        key: str,
        value: Any,
    ) -> None:
        """Set a metadata field on the session context.

        Used for industry_domain, signal_refs, etc.
        """
        context = await self.load(session_id)
        if not context:
            context = {"messages": [], "metadata": {}}

        context["metadata"][key] = value
        await self.save(
            session_id,
            context["messages"],
            context["metadata"],
        )

    async def get_messages_for_llm(
        self,
        session_id: UUID,
        system_prompt: str,
    ) -> list[dict[str, str]]:
        """Build the full message list for the LLM call.

        Prepends the system prompt, then appends cached context messages.

        Args:
            session_id: Chat session ID.
            system_prompt: System prompt to prepend.

        Returns:
            List of messages ready for the OpenAI API.
        """
        llm_messages = [{"role": "system", "content": system_prompt}]

        context = await self.load(session_id)
        if context and context.get("messages"):
            llm_messages.extend(context["messages"])

        return llm_messages

    async def clear(self, session_id: UUID) -> None:
        """Clear context for a session (on archive/delete)."""
        redis = await get_redis()
        key = self._key(session_id)
        await redis.delete(key)

    async def build_from_db(
        self,
        session_id: UUID,
        db_messages: list[Any],
        metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        """Build context from DB messages (cache miss fallback).

        Loads messages from ChatSessionRepository results into Redis.

        Args:
            session_id: Chat session ID.
            db_messages: ChatMessage model instances from DB.
            metadata: Optional session metadata.

        Returns:
            Formatted messages list.
        """
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in db_messages[-MAX_CONTEXT_MESSAGES:]
        ]

        await self.save(session_id, messages, metadata)
        return messages
