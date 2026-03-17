"""Pydantic schemas for Chat API endpoints.

Request/response models for chat sessions and messages.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ── Request Schemas ──────────────────────────────────────────────────


class CreateSessionRequest(BaseModel):
    """Request to create a new chat session."""

    industry_slug: str | None = Field(
        None,
        description="Industry slug to scope the session (e.g., 'fintech', 'energy').",
        examples=["fintech", "energy", "agriculture"],
    )
    title: str | None = Field(
        None,
        max_length=500,
        description="Optional session title. Auto-generated from first message if omitted.",
    )


class SendMessageRequest(BaseModel):
    """Request to send a message in a chat session."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="The user's chat message.",
    )


# ── Response Schemas ─────────────────────────────────────────────────


class ChatMessageResponse(BaseModel):
    """Individual chat message."""

    id: UUID
    session_id: UUID
    role: Literal["user", "assistant", "system"]
    content: str
    sources_json: dict[str, Any] | None = None
    token_count: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    """Chat session metadata (without messages)."""

    id: UUID
    user_id: UUID
    org_id: UUID
    industry_id: UUID | None = None
    title: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionDetailResponse(ChatSessionResponse):
    """Chat session with messages."""

    messages: list[ChatMessageResponse]


class ChatSessionListResponse(BaseModel):
    """List of chat sessions."""

    items: list[ChatSessionResponse]
    total: int
    skip: int = 0
    limit: int = 50


class ChatDeleteResponse(BaseModel):
    """Response for session deletion."""

    deleted: bool
    session_id: UUID
