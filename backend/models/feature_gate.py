"""Feature Gate model for database-driven feature flags"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class FeatureGate(Base):
    """
    Database-driven feature flags for tier/role-based gating.
    Allows runtime changes without code deployment.
    """

    __tablename__ = "feature_gates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Feature identifier
    feature_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Access requirements
    required_tier: Mapped[str] = mapped_column(String(50), nullable=False)
    required_role: Mapped[str | None] = mapped_column(String(50))

    # Enterprise flag
    is_enterprise_only: Mapped[bool] = mapped_column(Boolean, default=False)

    # Documentation
    description: Mapped[str | None] = mapped_column(Text)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<FeatureGate {self.feature_key} tier={self.required_tier}>"
