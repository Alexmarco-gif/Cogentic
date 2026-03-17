"""Add entity discovery fields and discovered_sources table.

Adds dynamic intelligence infrastructure:
1. Entity model: discovery_status + discovery_source columns
   - Makes entity creation transparent (seeded vs auto-discovered)
   - Enables confidence-tiered auto-creation from NER
2. discovered_sources table: tracks URLs found in signals
   - Powers the "living contracts" system
   - Enables dynamic source discovery and recommendation

Revision ID: 2026_03_05_0001
Revises: 2026_02_25_0002
Create Date: 2026-03-05 00:01:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_03_05_0001"
down_revision: Union[str, None] = "2026_02_25_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add entity discovery fields and discovered_sources table."""

    # ── 1. Add discovery columns to entities ─────────────────────────
    op.add_column(
        "entities",
        sa.Column(
            "discovery_status",
            sa.String(50),
            nullable=False,
            server_default="active",
            comment="active | pending_review | rejected — controls entity visibility",
        ),
    )
    op.add_column(
        "entities",
        sa.Column(
            "discovery_source",
            sa.String(50),
            nullable=False,
            server_default="seed",
            comment="seed | auto_extracted | agent | manual | system",
        ),
    )
    op.create_index("ix_entities_discovery_status", "entities", ["discovery_status"])
    op.create_index("ix_entities_discovery_source", "entities", ["discovery_source"])

    # ── 2. Create discovered_sources table ───────────────────────────
    op.create_table(
        "discovered_sources",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Source identity
        sa.Column("url", sa.Text, nullable=False),
        sa.Column(
            "url_hash",
            sa.String(64),
            nullable=False,
            comment="SHA-256 of normalized URL for dedup",
        ),
        sa.Column(
            "domain",
            sa.String(255),
            nullable=False,
            comment="Extracted domain (e.g., cbn.gov.ng)",
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=True,
            comment="Inferred source name",
        ),
        # Classification
        sa.Column(
            "source_type",
            sa.String(50),
            nullable=False,
            server_default="unknown",
            comment="Inferred: api | scraper | rss | social | government | research | news",
        ),
        sa.Column(
            "signal_type",
            sa.String(50),
            nullable=True,
            comment="Inferred signal type: regulatory, market, financial, news, etc.",
        ),
        # Discovery tracking
        sa.Column(
            "first_seen_signal_id",
            UUID(as_uuid=True),
            sa.ForeignKey("signals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "mention_count",
            sa.Integer,
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        # Scoring
        sa.Column(
            "relevance_score",
            sa.Float,
            nullable=False,
            server_default="0.5",
        ),
        # Lifecycle
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="discovered",
            comment="discovered | recommended | activated | dismissed",
        ),
        sa.Column(
            "activated_contract_id",
            UUID(as_uuid=True),
            sa.ForeignKey("signal_contracts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Metadata
        sa.Column("metadata", JSONB, server_default="{}"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # Indexes for discovered_sources
    op.create_index(
        "ix_discovered_sources_url_hash",
        "discovered_sources",
        ["url_hash"],
        unique=True,
    )
    op.create_index("ix_discovered_sources_domain", "discovered_sources", ["domain"])
    op.create_index("ix_discovered_sources_status", "discovered_sources", ["status"])
    op.create_index(
        "ix_discovered_sources_relevance",
        "discovered_sources",
        ["relevance_score"],
    )


def downgrade() -> None:
    """Remove entity discovery fields and discovered_sources table."""
    op.drop_table("discovered_sources")
    op.drop_index("ix_entities_discovery_status", table_name="entities")
    op.drop_index("ix_entities_discovery_source", table_name="entities")
    op.drop_column("entities", "discovery_source")
    op.drop_column("entities", "discovery_status")
