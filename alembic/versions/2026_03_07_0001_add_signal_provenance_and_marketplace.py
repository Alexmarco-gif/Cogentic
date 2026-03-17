"""Add signal provenance/versioning fields and signal marketplace tables.

- signals: add version, superseded_by_id, amended_at, provenance
- new table: signal_templates (marketplace catalog)
- new table: signal_template_subscriptions (per-org subscriptions)

Revision ID: 2026_03_07_0001
Revises: 2026_03_06_0002
Create Date: 2026-03-07 00:01:00.000000
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "2026_03_07_0001"
down_revision: Union[str, None] = "2026_03_06_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Extend signals table ───────────────────────────────────────────────

    op.add_column(
        "signals",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Monotonically increasing version counter per content_hash lineage",
        ),
    )
    op.add_column(
        "signals",
        sa.Column(
            "superseded_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("signals.id", ondelete="SET NULL"),
            nullable=True,
            comment="ID of the newer signal that supersedes this one (NULL = latest)",
        ),
    )
    op.add_column(
        "signals",
        sa.Column(
            "amended_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when this signal was superseded / amended",
        ),
    )
    op.add_column(
        "signals",
        sa.Column(
            "provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
            comment="Pipeline audit trail written by RefinementService step 10",
        ),
    )

    op.create_index(
        "ix_signals_superseded_by_id", "signals", ["superseded_by_id"], unique=False
    )
    op.create_index(
        "ix_signals_version", "signals", ["version"], unique=False
    )

    # ── 2. signal_templates ───────────────────────────────────────────────────

    op.create_table(
        "signal_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("short_description", sa.String(500), nullable=True),
        # Classification
        sa.Column(
            "industry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("industries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("signal_type", sa.String(50), nullable=False),
        # Geography
        sa.Column("primary_country", sa.String(3), nullable=True),
        sa.Column(
            "regions",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        # Source config (cloned into SignalContract on subscribe)
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column(
            "refresh_cron",
            sa.String(100),
            nullable=False,
            server_default="0 */1 * * *",
        ),
        sa.Column(
            "schedule_tier",
            sa.String(50),
            nullable=False,
            server_default="standard",
        ),
        sa.Column(
            "extraction_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        # Marketplace metadata
        sa.Column(
            "is_official",
            sa.Boolean,
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "is_featured",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "subscription_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "preview_signal_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_by_org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index("ix_signal_templates_name", "signal_templates", ["name"])
    op.create_index(
        "ix_signal_templates_slug", "signal_templates", ["slug"], unique=True
    )
    op.create_index(
        "ix_signal_templates_industry_id", "signal_templates", ["industry_id"]
    )
    op.create_index(
        "ix_signal_templates_signal_type", "signal_templates", ["signal_type"]
    )
    op.create_index(
        "ix_signal_templates_primary_country",
        "signal_templates",
        ["primary_country"],
    )
    op.create_index(
        "ix_signal_templates_is_featured", "signal_templates", ["is_featured"]
    )
    op.create_index(
        "ix_signal_templates_is_active", "signal_templates", ["is_active"]
    )

    # ── 3. signal_template_subscriptions ─────────────────────────────────────

    op.create_table(
        "signal_template_subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("signal_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contract_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("signal_contracts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "subscribed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_signal_template_subs_template_id",
        "signal_template_subscriptions",
        ["template_id"],
    )
    op.create_index(
        "ix_signal_template_subs_org_id",
        "signal_template_subscriptions",
        ["org_id"],
    )
    op.create_index(
        "ix_signal_template_subs_contract_id",
        "signal_template_subscriptions",
        ["contract_id"],
    )
    op.create_index(
        "ix_signal_template_subs_is_active",
        "signal_template_subscriptions",
        ["is_active"],
    )
    # Unique: one active sub per (template, org)
    op.create_index(
        "uq_signal_template_subs_template_org",
        "signal_template_subscriptions",
        ["template_id", "org_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("signal_template_subscriptions")
    op.drop_table("signal_templates")

    op.drop_index("ix_signals_version", table_name="signals")
    op.drop_index("ix_signals_superseded_by_id", table_name="signals")

    op.drop_column("signals", "provenance")
    op.drop_column("signals", "amended_at")
    op.drop_column("signals", "superseded_by_id")
    op.drop_column("signals", "version")
