"""Beta Account model for beta lifecycle tracking"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from backend.models.organization import Organization


class BetaAccount(Base, UUIDMixin):
    """
    Beta account lifecycle tracking.
    Manages notifications and transitions for beta pricing accounts.
    """

    __tablename__ = "beta_accounts"

    # Foreign key to organization
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Beta period
    beta_start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    beta_end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Discount configuration
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=50.00)

    # Notification flags
    notified_14d_before: Mapped[bool] = mapped_column(Boolean, default=False)
    notified_7d_before: Mapped[bool] = mapped_column(Boolean, default=False)

    # Transition status
    transitioned_to_standard: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    organization: Mapped["Organization"] = relationship(foreign_keys=[org_id])

    def __repr__(self) -> str:
        return f"<BetaAccount org={self.org_id} ends={self.beta_end_date}>"
