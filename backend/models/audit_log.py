"""Audit Log model (compliance trail)"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.organization import Organization
    from backend.models.user import User


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Immutable audit trail for compliance (SOC 2, ISO 27001)"""

    __tablename__ = "audit_logs"

    # Multi-tenant isolation
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    # Event details
    action: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # user.login, document.upload, document.delete, etc.
    resource_type: Mapped[str | None] = mapped_column(
        String(100)
    )  # document, user, organization
    resource_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True)

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45))  # IPv4 or IPv6
    user_agent: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(
        String(255)
    )  # Trace requests across services

    # Change tracking (for data modification events)
    changes: Mapped[dict | None] = mapped_column(
        JSON
    )  # {"before": {...}, "after": {...}}

    # Additional context data
    extra_data: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        name="metadata",  # Column name in DB is still "metadata"
    )

    # Relationships
    organization: Mapped["Organization"] = relationship()
    user: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} org={self.org_id}>"
