"""Organization model"""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
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

    # Tenant region / locale (Phase 5 — dynamic region support)
    default_country: Mapped[str | None] = mapped_column(
        String(3), nullable=True, comment="ISO 3166-1 alpha-3 country code (e.g. NGA)"
    )
    default_timezone: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="IANA timezone (e.g. Africa/Lagos)"
    )
    default_language: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="BCP-47 language tag (e.g. en, ha, yo)"
    )
    supported_regions: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        server_default="{}",
        comment="Additional region codes this tenant monitors",
    )

    # Pricing & Feature Gating
    pricing_tier: Mapped[str] = mapped_column(
        String(50), nullable=False, default="explorer", index=True
    )

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
