"""Add intelligence moat tables: entity graph, causal events, user feedback

Revision ID: 2026_02_12_0002
Revises: 2026_02_12_0001
Create Date: 2026-02-12 18:00:00.000000

Tables added:
  - entity_aliases: Structured alternate names for entities
  - entity_source_profiles: Cross-source data fusion layer
  - entity_relationships: Entity relationship graph (directed edges)
  - causal_events: Temporal event nodes for causal reasoning
  - causal_edges: Causal links between events
  - user_feedback: User interaction tracking for network effects

Columns added:
  - entities.verified: Manual verification flag
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "2026_02_12_0002"
down_revision = "2026_02_12_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add intelligence moat infrastructure tables."""

    # ── 1. Add verified column to entities ────────────────────────────
    op.add_column(
        "entities",
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
    )

    # ── 2. Entity Aliases ─────────────────────────────────────────────
    op.create_table(
        "entity_aliases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias_name", sa.String(255), nullable=False),
        sa.Column("alias_type", sa.String(50), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_entity_aliases_entity_id", "entity_aliases", ["entity_id"])
    op.create_index("ix_entity_aliases_alias_name", "entity_aliases", ["alias_name"])

    # ── 3. Entity Source Profiles ─────────────────────────────────────
    op.create_table(
        "entity_source_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(100), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=True),
        sa.Column("profile_data", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "entity_id", "source_type", name="uq_entity_source_profile"
        ),
    )
    op.create_index(
        "ix_entity_source_profiles_entity_id", "entity_source_profiles", ["entity_id"]
    )
    op.create_index(
        "ix_entity_source_profiles_source_type",
        "entity_source_profiles",
        ["source_type"],
    )

    # ── 4. Entity Relationships ───────────────────────────────────────
    op.create_table(
        "entity_relationships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_entity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_entity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(100), nullable=False),
        sa.Column("strength", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column(
            "bidirectional", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "evidence_signals", ARRAY(sa.String()), nullable=False, server_default="{}"
        ),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            name="uq_entity_relationship",
        ),
    )
    op.create_index(
        "ix_entity_rels_source", "entity_relationships", ["source_entity_id"]
    )
    op.create_index(
        "ix_entity_rels_target", "entity_relationships", ["target_entity_id"]
    )
    op.create_index(
        "ix_entity_rels_type", "entity_relationships", ["relationship_type"]
    )
    op.create_index(
        "ix_entity_rels_active",
        "entity_relationships",
        ["source_entity_id", "is_active"],
        postgresql_where=sa.text("is_active = true"),
    )

    # ── 5. Causal Events ──────────────────────────────────────────────
    op.create_table(
        "causal_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "signal_id",
            UUID(as_uuid=True),
            sa.ForeignKey("signals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_category", sa.String(50), nullable=False),
        sa.Column("event_summary", sa.Text(), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "entity_ids", ARRAY(sa.String()), nullable=False, server_default="{}"
        ),
        sa.Column("attributes", JSONB, nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_causal_events_signal_id", "causal_events", ["signal_id"])
    op.create_index("ix_causal_events_event_type", "causal_events", ["event_type"])
    op.create_index("ix_causal_events_category", "causal_events", ["event_category"])
    op.create_index("ix_causal_events_timestamp", "causal_events", ["event_timestamp"])

    # ── 6. Causal Edges ───────────────────────────────────────────────
    op.create_table(
        "causal_edges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cause_event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("causal_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "effect_event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("causal_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "relationship_label",
            sa.String(100),
            nullable=False,
            server_default="leads_to",
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("lag_days_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lag_days_max", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lag_days_avg", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "observation_count", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("p_value", sa.Float(), nullable=True),
        sa.Column("correlation", sa.Float(), nullable=True),
        sa.Column(
            "discovery_method", sa.String(50), nullable=False, server_default="manual"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_causal_edges_cause", "causal_edges", ["cause_event_id"])
    op.create_index("ix_causal_edges_effect", "causal_edges", ["effect_event_id"])

    # ── 7. User Feedback ──────────────────────────────────────────────
    op.create_table(
        "user_feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("feedback_type", sa.String(50), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("sentiment", sa.Float(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("context", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_user_feedback_user_id", "user_feedback", ["user_id"])
    op.create_index("ix_user_feedback_org_id", "user_feedback", ["org_id"])
    op.create_index("ix_user_feedback_type", "user_feedback", ["feedback_type"])
    op.create_index(
        "ix_user_feedback_target", "user_feedback", ["target_type", "target_id"]
    )
    op.create_index("ix_user_feedback_created", "user_feedback", ["created_at"])


def downgrade() -> None:
    """Remove intelligence moat tables."""
    op.drop_table("user_feedback")
    op.drop_table("causal_edges")
    op.drop_table("causal_events")
    op.drop_table("entity_relationships")
    op.drop_table("entity_source_profiles")
    op.drop_table("entity_aliases")
    op.drop_column("entities", "verified")
