"""Chat Message model"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.chat_session import ChatSession


class ChatMessage(Base, UUIDMixin, TimestampMixin):
    """Individual messages within a chat session.

    Context window management: last 10 messages sent as context to GPT-4o.
    Token count tracked per message for budget awareness.
    """

    __tablename__ = "chat_messages"

    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Message content
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Evidence/sources referenced in this message
    sources_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # Signal/brief references used in response

    # Token tracking (for context window management)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<ChatMessage session={self.session_id} role={self.role}>"
