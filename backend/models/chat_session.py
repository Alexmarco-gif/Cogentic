"""Chat Session model"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.chat_message import ChatMessage
    from backend.models.industry import Industry
    from backend.models.organization import Organization
    from backend.models.user import User


class ChatSession(Base, UUIDMixin, TimestampMixin):
    """AI Chat Agent conversation sessions.

    Session-with-memory architecture: last 10 messages as context.
    Supports function-calling to search signals, pull briefs, query entities.
    """

    __tablename__ = "chat_sessions"

    # Scoping
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    industry_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Session metadata
    title: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # Auto-generated from first message
    status: Mapped[str] = mapped_column(
        String(50), default="active", index=True
    )  # active, archived

    # Relationships
    user: Mapped["User"] = relationship()
    organization: Mapped["Organization"] = relationship()
    industry: Mapped["Industry | None"] = relationship()
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<ChatSession {self.id} user={self.user_id}>"
