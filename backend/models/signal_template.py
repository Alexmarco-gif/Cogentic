"""Signal Marketplace Template model.

A marketplace template is a reusable, subscribable signal contract blueprint.
Organizations can browse the marketplace, subscribe to templates, and
Cogent auto-creates the corresponding SignalContracts for their org.

Design:
- Templates are curated by Cogent (is_official=True) or community-created
- Subscriptions create a per-org SignalContract clone
- Tags, regions, and industries drive marketplace discovery
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.industry import Industry
    from backend.models.organization import Organization


class SignalTemplate(Base, UUIDMixin, TimestampMixin):
    """A marketplace template for a signal acquisition contract.

    Templates are the 'products' in the signal marketplace.
    An org subscribes → a SignalContract clone is created for that org.
    """

    __tablename__ = "signal_templates"

    # ── Identity ─────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Classification ────────────────────────────────────────────────
    industry_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # news, financial, regulatory, market, technology

    # Region / geography focus
    primary_country: Mapped[str | None] = mapped_column(
        String(3), nullable=True, index=True,
        comment="ISO 3166-1 alpha-3 (NGA, KEN, GHA, ZAF…)"
    )
    regions: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}",
        comment="Additional region codes covered (e.g. ['West Africa', 'ECOWAS'])"
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}",
        comment="Searchable tags (e.g. ['CBN', 'FX', 'inflation', 'fintech'])"
    )

    # ── Source configuration (cloned into SignalContract on subscribe) ──
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # api, scraper, rss, social
    refresh_cron: Mapped[str] = mapped_column(
        String(100), nullable=False, default="0 */1 * * *"
    )
    schedule_tier: Mapped[str] = mapped_column(
        String(50), nullable=False, default="standard"
    )
    extraction_config: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )

    # ── Marketplace metadata ──────────────────────────────────────────
    is_official: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
        comment="True = curated by Cogent; False = community-submitted"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscription_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Cached count of active subscriptions (updated on subscribe/unsubscribe)"
    )
    preview_signal_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
        comment="Approximate number of signals generated per day"
    )

    # Author (NULL = Cogent-official)
    created_by_org_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────────────
    industry: Mapped["Industry"] = relationship()
    created_by_org: Mapped["Organization | None"] = relationship()
    subscriptions: Mapped[list["SignalTemplateSubscription"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SignalTemplate {self.slug} country={self.primary_country}>"


class SignalTemplateSubscription(Base, UUIDMixin, TimestampMixin):
    """An org's subscription to a marketplace template.

    When an org subscribes, a SignalContract is created for their org
    (cloned from the template's source config).
    """

    __tablename__ = "signal_template_subscriptions"

    template_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("signal_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The contract that was auto-created for this org upon subscription
    contract_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("signal_contracts.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subscribed_at: Mapped[datetime] = mapped_column(
        __import__("sqlalchemy").DateTime(timezone=True),
        server_default=__import__("sqlalchemy").func.now(),
        nullable=False,
    )

    # Relationships
    template: Mapped["SignalTemplate"] = relationship(back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<SignalTemplateSubscription org={self.org_id} template={self.template_id}>"
