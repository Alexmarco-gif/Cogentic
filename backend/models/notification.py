"""Notification model — persistent in-app notifications per organisation."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDMixin


class Notification(Base, UUIDMixin, TimestampMixin):
    """Persistent in-app notification scoped to an organisation.

    Notifications are written when notable platform events occur
    (high-confidence signals, contract warnings, system alerts) and
    remain readable until explicitly dismissed.  Per-user read state
    is tracked via ``read_at``.
    """

    __tablename__ = "notifications"

    # Owning organisation (required — all notifications are org-scoped)
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Notification category: "signal" | "contract" | "system"
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Human-readable content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Source entity that triggered this notification (used for dedup + deep-link)
    source_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g. "signal", "contract"
    source_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )  # UUID of the originating entity

    # Dismiss / read tracking
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
