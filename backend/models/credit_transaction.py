"""Credit Transaction model for tracking credit consumption"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from backend.models.organization import Organization
    from backend.models.user import User


class CreditTransaction(Base, UUIDMixin):
    """Audit trail for credit consumption"""

    __tablename__ = "credit_transactions"

    # Foreign keys
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )

    # Transaction details
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    credits_consumed: Mapped[int] = mapped_column(Integer, nullable=False)
    credits_remaining: Mapped[int] = mapped_column(Integer, nullable=False)

    # Metadata for additional context
    metadata: Mapped[dict | None] = mapped_column(JSONB)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships (optional, for easier queries)
    organization: Mapped["Organization"] = relationship(foreign_keys=[org_id])
    user: Mapped["User | None"] = relationship(foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<CreditTransaction org={self.org_id} action={self.action_type} credits={self.credits_consumed}>"
