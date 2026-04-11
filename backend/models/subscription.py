"""Subscription model (billing & plan management)."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.organization import Organization


class Subscription(Base, UUIDMixin, TimestampMixin):
    """Billing & subscription management across payment providers."""

    __tablename__ = "subscriptions"

    # One-to-one with organization
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Legacy Stripe placeholders (kept for backward compatibility)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), unique=True)

    # Active payment provider state
    provider: Mapped[str | None] = mapped_column(String(50), index=True)
    provider_customer_code: Mapped[str | None] = mapped_column(
        String(255), unique=True
    )
    provider_plan_code: Mapped[str | None] = mapped_column(String(255), index=True)
    provider_subscription_code: Mapped[str | None] = mapped_column(
        String(255), unique=True
    )
    provider_email_token: Mapped[str | None] = mapped_column(String(255))
    latest_reference: Mapped[str | None] = mapped_column(String(255), index=True)
    authorization_code: Mapped[str | None] = mapped_column(String(255))
    provider_metadata: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )

    # Plan details
    plan_tier: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # explorer, growth, mid_market, enterprise
    billing_cycle: Mapped[str | None] = mapped_column(String(50))  # monthly, annual

    # Pricing (in cents)
    price_cents: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="active", index=True
    )  # active, past_due, canceled, trialing
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )

    # Usage tracking (for metered billing)
    usage_current_period: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )  # {"documents": 45, "ai_jobs": 120}

    # Cancellation
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="subscription")

    def __repr__(self) -> str:
        return f"<Subscription org={self.org_id} plan={self.plan_tier}>"
