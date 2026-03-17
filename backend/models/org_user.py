"""Organization-User membership model"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.organization import Organization
    from backend.models.user import User


class OrgUser(Base, UUIDMixin, TimestampMixin):
    """Many-to-many relationship between organizations and users"""

    __tablename__ = "org_users"
    __table_args__ = (UniqueConstraint("org_id", "user_id", name="uq_org_user"),)

    # Foreign keys
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role-based access control
    role: Mapped[str] = mapped_column(
        String(50), default="member", nullable=False, index=True
    )  # owner, admin, member, viewer

    # Invitation tracking
    invited_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # active, suspended, pending

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(
        back_populates="organizations", foreign_keys=[user_id]
    )

    def __repr__(self) -> str:
        return f"<OrgUser org={self.org_id} user={self.user_id} role={self.role}>"
