"""Add regulatory knowledge tables for dynamic Nigerian regulatory intelligence

Revision ID: 2026_02_14_0001
Revises: 2026_02_13_0001
Create Date: 2026-02-14 00:01:00.000000

This migration adds 4 tables for learning-based regulatory intelligence:
  1. regulatory_events — tracks policy changes, enforcement actions, deadlines
  2. regulatory_rules — stores dynamic business rules (NOT hardcoded)
  3. regulatory_impacts — records observed outcomes for learning loops
  4. regulatory_patterns — learned patterns about regulatory behavior

Design philosophy:
  - Auto-extraction from signals using NLP patterns
  - Expert verification and feedback for confidence scoring
  - JSON-based rule logic (not hardcoded conditions)
  - Semantic search via pgvector embeddings
  - Temporal validity tracking (effective_from, effective_until)
  - Learning metrics (confidence_score, accuracy_score, application_count)
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_02_14_0001"
down_revision: Union[str, None] = "2026_02_13_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create regulatory knowledge tables"""

    # =========================================================================
    # 1. REGULATORY_EVENTS — Policy changes, enforcement, deadlines
    # =========================================================================
    op.create_table(
        "regulatory_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("issuing_body", sa.String(100), nullable=False, index=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("announced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("severity_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("compliance_complexity", sa.String(20), nullable=True),
        sa.Column("affected_sectors", ARRAY(sa.String(100)), nullable=True),
        sa.Column("affected_entity_types", ARRAY(sa.String(100)), nullable=True),
        sa.Column("requirements", JSONB, nullable=True),
        sa.Column("exemptions", JSONB, nullable=True),
        sa.Column("penalties", JSONB, nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("source_document_path", sa.String(500), nullable=True),
        sa.Column("source_signal_id", UUID(as_uuid=True), nullable=True),
        sa.Column("source_event_id", UUID(as_uuid=True), nullable=True),
        sa.Column("historical_precedents", ARRAY(UUID(as_uuid=True)), nullable=True),
        sa.Column(
            "content_embedding", sa.dialects.postgresql.VECTOR(1536), nullable=True
        ),
        sa.Column("verified_by_expert", sa.Boolean(), default=False, nullable=False),
        sa.Column("confidence_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            onupdate=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_signal_id"], ["signals.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["source_event_id"], ["regulatory_events.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )

    # Indexes for regulatory_events
    op.create_index(
        "ix_regulatory_events_effective_from", "regulatory_events", ["effective_from"]
    )
    op.create_index(
        "ix_regulatory_events_deadline_date", "regulatory_events", ["deadline_date"]
    )
    op.create_index(
        "ix_regulatory_events_sectors",
        "regulatory_events",
        ["affected_sectors"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_regulatory_events_entity_types",
        "regulatory_events",
        ["affected_entity_types"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_regulatory_events_verified", "regulatory_events", ["verified_by_expert"]
    )

    # =========================================================================
    # 2. REGULATORY_RULES — Dynamic business rules (JSON logic)
    # =========================================================================
    op.create_table(
        "regulatory_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", UUID(as_uuid=True), nullable=False),
        sa.Column("rule_type", sa.String(50), nullable=False, index=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("condition", JSONB, nullable=False),
        sa.Column("action", JSONB, nullable=False),
        sa.Column("priority", sa.Integer(), default=50, nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False, index=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("application_count", sa.Integer(), default=0, nullable=False),
        sa.Column("accuracy_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("interpretation_guidance", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            onupdate=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["regulatory_events.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )

    # Indexes for regulatory_rules
    op.create_index("ix_regulatory_rules_event_id", "regulatory_rules", ["event_id"])
    op.create_index("ix_regulatory_rules_priority", "regulatory_rules", ["priority"])
    op.create_index(
        "ix_regulatory_rules_effective_from", "regulatory_rules", ["effective_from"]
    )

    # =========================================================================
    # 3. REGULATORY_IMPACTS — Observed outcomes (learning loop)
    # =========================================================================
    op.create_table(
        "regulatory_impacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", UUID(as_uuid=True), nullable=True),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("impact_type", sa.String(50), nullable=False, index=True),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("baseline_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("post_impact_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("percentage_change", sa.Numeric(10, 4), nullable=True),
        sa.Column("lag_days", sa.Integer(), nullable=True),
        sa.Column("observation_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supporting_signal_ids", ARRAY(UUID(as_uuid=True)), nullable=True),
        sa.Column("evidence_quality", sa.String(20), nullable=True),
        sa.Column("confounding_factors", JSONB, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            onupdate=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["regulatory_events.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"], ["regulatory_rules.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
    )

    # Indexes for regulatory_impacts
    op.create_index(
        "ix_regulatory_impacts_event_id", "regulatory_impacts", ["event_id"]
    )
    op.create_index("ix_regulatory_impacts_rule_id", "regulatory_impacts", ["rule_id"])
    op.create_index(
        "ix_regulatory_impacts_entity_id", "regulatory_impacts", ["entity_id"]
    )
    op.create_index(
        "ix_regulatory_impacts_observation_date",
        "regulatory_impacts",
        ["observation_date"],
    )

    # =========================================================================
    # 4. REGULATORY_PATTERNS — Learned sequences and behaviors
    # =========================================================================
    op.create_table(
        "regulatory_patterns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pattern_type", sa.String(50), nullable=False, index=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trigger_conditions", JSONB, nullable=False),
        sa.Column("sequence", JSONB, nullable=False),
        sa.Column("typical_impacts", JSONB, nullable=True),
        sa.Column("frequency_count", sa.Integer(), default=1, nullable=False),
        sa.Column("prediction_accuracy", sa.Numeric(3, 2), nullable=True),
        sa.Column("confidence_interval_lower", sa.Numeric(3, 2), nullable=True),
        sa.Column("confidence_interval_upper", sa.Numeric(3, 2), nullable=True),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            onupdate=sa.text("NOW()"),
            nullable=False,
        ),
    )

    # Indexes for regulatory_patterns
    op.create_index(
        "ix_regulatory_patterns_frequency", "regulatory_patterns", ["frequency_count"]
    )
    op.create_index(
        "ix_regulatory_patterns_accuracy",
        "regulatory_patterns",
        ["prediction_accuracy"],
    )


def downgrade() -> None:
    """Drop regulatory knowledge tables"""
    op.drop_table("regulatory_patterns")
    op.drop_table("regulatory_impacts")
    op.drop_table("regulatory_rules")
    op.drop_table("regulatory_events")
