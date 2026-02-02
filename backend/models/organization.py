"""Organization model"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Integer, String, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.org_user import OrgUser
    from backend.models.subscription import Subscription
    from backend.models.api_key import APIKey


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
    settings: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    max_users: Mapped[int] = mapped_column(Integer, default=10)
    max_storage_gb: Mapped[int] = mapped_column(Integer, default=10)

    # Subscription reference
    subscription_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))

    # Compliance (GDPR data residency)
    data_region: Mapped[str] = mapped_column(String(50), default="us-east")

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
