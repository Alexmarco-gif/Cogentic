"""Chat API endpoints with SSE streaming.

Provides:
  - POST   /chat/sessions          → Create a new chat session
  - GET    /chat/sessions          → List user's chat sessions
  - GET    /chat/sessions/{id}     → Get session with messages
  - POST   /chat/sessions/{id}/messages → Send message (SSE stream)
  - PATCH  /chat/sessions/{id}/archive  → Archive a session
  - DELETE /chat/sessions/{id}     → Delete a session
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.redis_client import get_redis
from backend.schemas.chat import (
    ChatDeleteResponse,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    CreateSessionRequest,
    SendMessageRequest,
)
from backend.services.chat_agent_service import ChatAgentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat")


# ── Session Endpoints ────────────────────────────────────────────────


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=201,
    summary="Create a new chat session",
)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Create a new AI chat session.

    Optionally scope by industry for domain-specific responses.
    """
    redis = await get_redis()
    service = ChatAgentService(db, redis, auth.org_id, auth.user_id)

    session = await service.create_session(
        industry_slug=body.industry_slug,
        title=body.title,
    )
    return ChatSessionResponse.model_validate(session)


@router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    summary="List user's chat sessions",
)
async def list_sessions(
    status: str | None = Query("active", pattern=r"^(active|archived)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get a list of the current user's chat sessions."""
    redis = await get_redis()
    service = ChatAgentService(db, redis, auth.org_id, auth.user_id)

    sessions = await service.list_sessions(status=status, skip=skip, limit=limit)

    return ChatSessionListResponse(
        sessions=[ChatSessionResponse.model_validate(s) for s in sessions],
        total=len(sessions),
    )


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionDetailResponse,
    summary="Get session with full message history",
)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get a chat session with all messages."""
    redis = await get_redis()
    service = ChatAgentService(db, redis, auth.org_id, auth.user_id)

    session = await service.get_session(session_id)
    if not session:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Chat session not found")

    return ChatSessionDetailResponse.model_validate(session)


# ── Message Endpoint (SSE Streaming) ─────────────────────────────────


@router.post(
    "/sessions/{session_id}/messages",
    summary="Send a message and stream AI response via SSE",
    responses={
        200: {
            "description": "SSE stream of agent events",
            "content": {"text/event-stream": {}},
        },
    },
)
async def send_message(
    session_id: UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Send a message to the AI chat agent.

    Returns a Server-Sent Events (SSE) stream with the following event types:
      - `thinking`       — Agent is processing
      - `tool_call`      — Agent invoked a tool
      - `tool_result`    — Tool returned results
      - `content`        — Text chunk from the AI (stream to chat bubble)
      - `citation`       — A source reference
      - `recommendation` — Actionable recommendation
      - `done`           — Agent finished (includes metadata)
      - `error`          — An error occurred
    """
    redis = await get_redis()
    service = ChatAgentService(db, redis, auth.org_id, auth.user_id)

    async def event_generator():
        async for event in service.send_message(session_id, body.message):
            yield event.to_sse()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Session Lifecycle ────────────────────────────────────────────────


@router.patch(
    "/sessions/{session_id}/archive",
    response_model=ChatSessionResponse,
    summary="Archive a chat session",
)
async def archive_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Archive a chat session. Messages are preserved but session is marked inactive."""
    redis = await get_redis()
    service = ChatAgentService(db, redis, auth.org_id, auth.user_id)

    session = await service.archive_session(session_id)
    if not session:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Chat session not found")

    return ChatSessionResponse.model_validate(session)


@router.delete(
    "/sessions/{session_id}",
    response_model=ChatDeleteResponse,
    summary="Delete a chat session",
)
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Permanently delete a chat session and all its messages."""
    redis = await get_redis()
    service = ChatAgentService(db, redis, auth.org_id, auth.user_id)

    deleted = await service.delete_session(session_id)
    if not deleted:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Chat session not found")

    return ChatDeleteResponse(deleted=True, session_id=session_id)
