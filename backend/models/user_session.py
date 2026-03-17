"""
SQLAlchemy model for user_sessions table.

Records every authenticated device/session so we can show users
their active sessions without relying on Auth0's paid Sessions add-on.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDMixin


class UserSession(Base, UUIDMixin, TimestampMixin):
    """A single device/browser session for an authenticated user."""

    __tablename__ = "user_sessions"

    # ── Columns ───────────────────────────────────────────────────────────

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Parsed device string, e.g. "Chrome 123 on macOS"
    device: Mapped[str] = mapped_column(String(255), nullable=False, default="Unknown")

    # Raw User-Agent header (for debugging / display)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Client IP (IPv4 or IPv6)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)

    # Updated on every authenticated request
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Soft-revoke — set when user terminates the session manually
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # ── Indexes ───────────────────────────────────────────────────────────

    __table_args__ = (
        Index("ix_user_sessions_user_id_last_active", "user_id", "last_active_at"),
    )

    # ── Helpers ───────────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """Session has not been revoked."""
        return self.revoked_at is None

    def __repr__(self) -> str:
        return (
            f"<UserSession id={self.id} user_id={self.user_id} "
            f"device={self.device!r} ip={self.ip_address}>"
        )
