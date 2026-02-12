"""Chat Session repository"""

import time
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.chat_message import ChatMessage
from backend.models.chat_session import ChatSession
from backend.repositories.audit import audit_logger
from backend.repositories.base import TenantRepository


class ChatSessionRepository(TenantRepository[ChatSession]):
    """Repository for chat session operations.

    Chat sessions are tenant-scoped (org_id + user_id).
    Session-with-memory architecture: last 10 messages as context.
    """

    def __init__(
        self,
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID | None = None,
        request_id: str | None = None,
    ):
        super().__init__(ChatSession, db, org_id, user_id, request_id)

    async def get_user_sessions(
        self,
        user_id: UUID,
        *,
        status: str | None = "active",
        skip: int = 0,
        limit: int = 50,
    ) -> list[ChatSession]:
        """Get all sessions for a user (within current org)"""
        start_time = time.time()

        query = select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.org_id == self.org_id,
        )
        if status:
            query = query.where(ChatSession.status == status)

        result = await self.db.execute(
            query.order_by(desc(ChatSession.updated_at)).offset(skip).limit(limit)
        )
        records = list(result.scalars().all())

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=self.org_id,
            table="chat_sessions",
            action="list_user_sessions",
            filters={"user_id": user_id, "status": status},
            result_count=len(records),
            duration_ms=duration_ms,
            request_id=self.request_id,
        )
        return records

    async def get_with_messages(
        self,
        session_id: UUID,
    ) -> ChatSession | None:
        """Get a session with all messages pre-loaded (full history)"""
        result = await self.db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(
                ChatSession.id == session_id,
                ChatSession.org_id == self.org_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_recent_messages(
        self,
        session_id: UUID,
        *,
        limit: int = 10,
    ) -> list[ChatMessage]:
        """Get last N messages for context window (session-with-memory).

        Default: last 10 messages as per WP-0.2 spec.
        """
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        # Reverse so oldest message is first (chronological order)
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    async def add_message(
        self,
        session_id: UUID,
        *,
        role: str,
        content: str,
        sources_json: dict | None = None,
        token_count: int | None = None,
    ) -> ChatMessage:
        """Add a message to a session"""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            sources_json=sources_json,
            token_count=token_count,
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def get_message_count(self, session_id: UUID) -> int:
        """Count total messages in a session"""
        result = await self.db.execute(
            select(func.count(ChatMessage.id)).where(
                ChatMessage.session_id == session_id
            )
        )
        return result.scalar_one()

    async def archive_session(self, session_id: UUID) -> ChatSession | None:
        """Archive a session (set status to 'archived')"""
        return await self.update(session_id, status="archived")
