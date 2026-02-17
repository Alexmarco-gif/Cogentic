"""Pricing Configuration model for dynamic pricing settings"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.user import User


class PricingConfig(Base):
    """Global pricing configuration (single source of truth)"""

    __tablename__ = "pricing_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Configuration key-value
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    config_value: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Audit trail
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Relationship (optional)
    updated_by_user: Mapped["User | None"] = relationship(foreign_keys=[updated_by])

    def __repr__(self) -> str:
        return f"<PricingConfig {self.config_key}={self.config_value}>"
