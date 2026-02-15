"""Chat Agent Service — orchestrates sessions, messages, rate limiting, and the agent.

This is the main service layer between the API endpoints and the ChatAgent core.
It handles:
  - Session lifecycle (create, load, list, archive, auto-title)
  - Message persistence (user + assistant messages to DB)
  - Rate limiting (30 msg/min per user via Redis)
  - Agent invocation (ChatAgent.run())
  - Token estimation for budget tracking
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.agent import ChatAgent, SSEEvent
from backend.models.chat_session import ChatSession
from backend.models.industry import Industry
from backend.repositories.chat_session import ChatSessionRepository

logger = logging.getLogger(__name__)

# Rate limiting constants
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 30  # messages per window
RATE_LIMIT_KEY_PREFIX = "chat:ratelimit"

# Token estimation (rough: 1 token ≈ 4 chars)
CHARS_PER_TOKEN = 4


class ChatAgentService:
    """Service orchestrating the AI Chat Agent.

    Usage (from API layer):
        service = ChatAgentService(db, redis, org_id, user_id)
        session = await service.create_session(industry_slug="fintech")
        async for event in service.send_message(session.id, "What's trending?"):
            yield event.to_sse()
    """

    def __init__(
        self,
        db: AsyncSession,
        redis: Any,
        org_id: UUID,
        user_id: UUID,
    ):
        self.db = db
        self.redis = redis
        self.org_id = org_id
        self.user_id = user_id
        self.repo = ChatSessionRepository(db, org_id, user_id)

    # ── Session Management ───────────────────────────────────────────

    async def create_session(
        self,
        *,
        industry_slug: str | None = None,
        title: str | None = None,
    ) -> ChatSession:
        """Create a new chat session.

        Args:
            industry_slug: Optional industry slug to scope the session.
            title: Optional title. Auto-generated from first message if None.

        Returns:
            The created ChatSession.
        """
        industry_id = None
        if industry_slug:
            result = await self.db.execute(
                select(Industry).where(Industry.slug == industry_slug)
            )
            industry = result.scalar_one_or_none()
            if industry:
                industry_id = industry.id

        session = ChatSession(
            user_id=self.user_id,
            org_id=self.org_id,
            industry_id=industry_id,
            title=title,
            status="active",
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)

        logger.info(
            f"Created chat session {session.id} for user={self.user_id} "
            f"org={self.org_id} industry={industry_slug}"
        )
        return session

    async def get_session(self, session_id: UUID) -> ChatSession | None:
        """Get a session by ID (with org/user scoping)."""
        return await self.repo.get_with_messages(session_id)

    async def list_sessions(
        self,
        *,
        status: str | None = "active",
        skip: int = 0,
        limit: int = 50,
    ) -> list[ChatSession]:
        """List user's chat sessions."""
        return await self.repo.get_user_sessions(
            self.user_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    async def archive_session(self, session_id: UUID) -> ChatSession | None:
        """Archive a chat session."""
        session = await self.repo.archive_session(session_id)
        if session:
            # Clear Redis context cache
            cache_key = f"chat:context:{session_id}"
            await self.redis.delete(cache_key)
            logger.info(f"Archived chat session {session_id}")
        return session

    async def delete_session(self, session_id: UUID) -> bool:
        """Permanently delete a chat session and all messages."""
        session = await self.repo.get(session_id)
        if not session:
            return False

        await self.db.delete(session)
        await self.db.flush()

        # Clear Redis context cache
        cache_key = f"chat:context:{session_id}"
        await self.redis.delete(cache_key)

        logger.info(f"Deleted chat session {session_id}")
        return True

    # ── Message Handling ─────────────────────────────────────────────

    async def send_message(
        self,
        session_id: UUID,
        message: str,
    ) -> AsyncGenerator[SSEEvent, None]:
        """Send a user message and stream the agent's response.

        This is the main entry point. It:
          1. Validates the session exists and belongs to the user
          2. Checks rate limits
          3. Persists the user message
          4. Runs the ChatAgent
          5. Persists the assistant response
          6. Auto-generates session title if needed

        Args:
            session_id: The chat session UUID.
            message: The user's message text.

        Yields:
            SSEEvent objects for real-time streaming.
        """
        # ── 1. Validate session ──────────────────────────────────────
        session = await self.repo.get(session_id)
        if not session:
            yield SSEEvent(
                event="error",
                data={
                    "code": "session_not_found",
                    "message": "Chat session not found.",
                },
            )
            return

        if session.status != "active":
            yield SSEEvent(
                event="error",
                data={
                    "code": "session_archived",
                    "message": "This session is archived.",
                },
            )
            return

        # ── 2. Rate limiting ─────────────────────────────────────────
        rate_ok = await self._check_rate_limit()
        if not rate_ok:
            yield SSEEvent(
                event="error",
                data={
                    "code": "rate_limited",
                    "message": f"Rate limit exceeded. Maximum {RATE_LIMIT_MAX} messages per minute.",
                },
            )
            return

        # ── 3. Persist user message ──────────────────────────────────
        user_token_count = _estimate_tokens(message)
        await self.repo.add_message(
            session_id,
            role="user",
            content=message,
            token_count=user_token_count,
        )

        # ── 4. Resolve industry code ─────────────────────────────────
        industry_code = None
        if session.industry_id:
            result = await self.db.execute(
                select(Industry.slug).where(Industry.id == session.industry_id)
            )
            industry_code = result.scalar_one_or_none()

        # ── 5. Run the agent ─────────────────────────────────────────
        agent = ChatAgent(
            session_id=session_id,
            org_id=self.org_id,
            user_id=self.user_id,
            industry_code=industry_code,
        )

        assistant_content = ""
        all_citations: list[dict] = []

        async for event in agent.run(message, self.db, self.redis):
            # Capture assistant content for persistence
            if event.event == "content":
                assistant_content += event.data.get("text", "")
            elif event.event == "citation":
                all_citations.append(event.data)

            yield event

        # ── 6. Persist assistant response ────────────────────────────
        if assistant_content:
            assistant_token_count = _estimate_tokens(assistant_content)
            sources_json = {"citations": all_citations} if all_citations else None

            await self.repo.add_message(
                session_id,
                role="assistant",
                content=assistant_content,
                sources_json=sources_json,
                token_count=assistant_token_count,
            )

        # ── 7. Auto-generate title ───────────────────────────────────
        if not session.title:
            await self._auto_title(session, message)

    # ── Rate Limiting ────────────────────────────────────────────────

    async def _check_rate_limit(self) -> bool:
        """Check if user is within rate limits.

        Uses Redis sliding window: 30 messages per 60 seconds.

        Returns:
            True if request is allowed, False if rate-limited.
        """
        key = f"{RATE_LIMIT_KEY_PREFIX}:{self.user_id}"

        try:
            current = await self.redis.get(key)
            if current is not None and int(current) >= RATE_LIMIT_MAX:
                logger.warning(
                    f"Rate limit hit for user {self.user_id}: {current}/{RATE_LIMIT_MAX}"
                )
                return False

            pipe = self.redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, RATE_LIMIT_WINDOW)
            await pipe.execute()
            return True

        except Exception as e:
            # If Redis is down, allow the request (fail open)
            logger.error(f"Rate limit check failed: {e}")
            return True

    # ── Auto Title ───────────────────────────────────────────────────

    async def _auto_title(self, session: ChatSession, first_message: str) -> None:
        """Generate a session title from the first user message.

        Simple heuristic: truncate to 80 chars + ellipsis.
        We don't burn an LLM call for this.
        """
        title = first_message.strip()
        if len(title) > 80:
            title = title[:77] + "..."

        session.title = title
        await self.db.flush()


# ── Utility Functions ────────────────────────────────────────────────


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (1 token ≈ 4 characters).

    Good enough for budget tracking. For precise counts,
    use tiktoken (but it's slower and not needed here).
    """
    return max(1, len(text) // CHARS_PER_TOKEN)
