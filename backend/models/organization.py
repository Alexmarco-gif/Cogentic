"""Organization model"""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.api_key import APIKey
    from backend.models.org_user import OrgUser
    from backend.models.subscription import Subscription


class Organization(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Multi-tenant organization entity"""

    __tablename__ = "organizations"

    # Core identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )

    # Contact & billing
    billing_email: Mapped[str | None] = mapped_column(String(255))

    # Feature flags & limits
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    max_users: Mapped[int] = mapped_column(Integer, default=10)
    max_storage_gb: Mapped[int] = mapped_column(Integer, default=10)

    # Compliance (GDPR data residency)
    data_region: Mapped[str] = mapped_column(String(50), default="us-east")

    # Pricing & Feature Gating
    pricing_tier: Mapped[str] = mapped_column(
        String(50), nullable=False, default="explorer", index=True
    )

    # Beta Pricing (DEPRECATED — prefer BetaAccount table for beta lifecycle)
    # These fields are kept for backward compatibility during migration.
    # New code should use BetaAccount queries instead.
    is_beta_account: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    beta_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    beta_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    beta_discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=50.00)

    # Trial Management
    trial_status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    trial_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    billing_cycle_start: Mapped[date | None] = mapped_column(Date)

    # Credit System
    credits_allocated_monthly: Mapped[int] = mapped_column(Integer, default=0)
    credits_consumed: Mapped[int] = mapped_column(Integer, default=0)
    credits_overage_rate: Mapped[float] = mapped_column(Numeric(10, 2), default=0.10)

    # Relationships
    members: Mapped[list["OrgUser"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="organization", uselist=False
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Organization {self.slug}>"
