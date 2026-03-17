"""Dynamic Knowledge Base model.

Stores domain-agnostic reference data that used to be hardcoded:
- Regulatory bodies (per country/region)
- Industry sectors and their keyword signatures
- Entity type classifications
- Domain definitions (e.g. "E-Commerce & Retail")

All keyed by `category` so a single table serves multiple lookup needs.
"""

from sqlalchemy import Float, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDMixin


class KnowledgeEntry(Base, UUIDMixin, TimestampMixin):
    """Generic knowledge base entry — replaces all hardcoded lookup dicts."""

    __tablename__ = "knowledge_entries"

    # ── Lookup key ────────────────────────────────────────────────────────
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Logical category: 'regulatory_body', 'sector', 'entity_type', 'domain'",
    )

    # ── Scoping ───────────────────────────────────────────────────────────
    country: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
        index=True,
        comment="ISO 3166-1 alpha-3 country code (e.g. NGA). NULL = global.",
    )
    region: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Geographic region (e.g. 'West Africa'). NULL = country-wide.",
    )

    # ── Identity ──────────────────────────────────────────────────────────
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Short code / acronym (e.g. 'CBN', 'fintech', 'E-Commerce & Retail')",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable name (e.g. 'Central Bank of Nigeria')",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional long description"
    )

    # ── Matching ──────────────────────────────────────────────────────────
    aliases: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        server_default="{}",
        comment="Alternative names / search keywords for fuzzy matching",
    )
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
        server_default="{}",
        comment="NLP keyword triggers for automatic extraction",
    )

    # ── Metadata ──────────────────────────────────────────────────────────
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
        comment="Extensible JSON metadata (e.g. color, icon, parent sector)",
    )

    # ── Ordering ──────────────────────────────────────────────────────────
    sort_order: Mapped[int] = mapped_column(
        default=0, server_default="0", comment="Display ordering within category"
    )

    # ── Confidence / provenance ───────────────────────────────────────────
    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        server_default="1.0",
        comment="1.0 = expert-verified, 0.7 = auto-extracted",
    )
    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Where this entry came from (e.g. 'seed', 'expert', 'auto-extract')",
    )

    __table_args__ = (
        Index("ix_knowledge_category_country", "category", "country"),
        Index("ix_knowledge_category_code", "category", "code", unique=True),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeEntry {self.category}/{self.code}>"
