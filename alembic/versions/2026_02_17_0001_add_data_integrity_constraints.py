"""Add data integrity constraints — FK, indexes, unique constraints.

Phase 3 items: 3.1 (AIUsageLog FKs), 3.2 (missing FK indexes),
3.3 (missing unique constraints).

Revision ID: 2026_02_17_0001
Revises: 2026_02_16_0001
Create Date: 2026-02-17 00:01:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_02_17_0001"
down_revision: Union[str, None] = "2026_02_16_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 3.1  FK constraints on ai_usage_logs ─────────────────────────
    op.create_foreign_key(
        "fk_ai_usage_logs_user_id",
        "ai_usage_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_ai_usage_logs_org_id",
        "ai_usage_logs",
        "organizations",
        ["org_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ── 3.2  Missing indexes on FK columns ───────────────────────────
    op.create_index(
        "ix_regulatory_rules_event_id", "regulatory_rules", ["event_id"]
    )
    op.create_index(
        "ix_regulatory_impacts_event_id", "regulatory_impacts", ["event_id"]
    )
    op.create_index(
        "ix_regulatory_impacts_rule_id", "regulatory_impacts", ["rule_id"]
    )
    op.create_index(
        "ix_regulatory_impacts_entity_id", "regulatory_impacts", ["entity_id"]
    )
    op.create_index(
        "ix_ai_jobs_user_id", "ai_jobs", ["user_id"]
    )
    op.create_index(
        "ix_credit_transactions_user_id", "credit_transactions", ["user_id"]
    )
    op.create_index(
        "ix_regulatory_events_source_signal_id",
        "regulatory_events",
        ["source_signal_id"],
    )
    op.create_index(
        "ix_regulatory_events_source_event_id",
        "regulatory_events",
        ["source_event_id"],
    )
    op.create_index(
        "ix_regulatory_events_created_by", "regulatory_events", ["created_by"]
    )
    op.create_index(
        "ix_regulatory_rules_created_by", "regulatory_rules", ["created_by"]
    )
    op.create_index(
        "ix_regulatory_impacts_recorded_by", "regulatory_impacts", ["recorded_by"]
    )

    # ── 3.3  Missing unique constraints ──────────────────────────────
    op.create_unique_constraint(
        "uq_signal_scores_signal_type",
        "signal_scores",
        ["signal_id", "score_type"],
    )
    op.create_unique_constraint(
        "uq_ml_model_registry_name_version",
        "ml_model_registry",
        ["model_name", "model_version"],
    )
    op.create_unique_constraint(
        "uq_entity_aliases_entity_alias",
        "entity_aliases",
        ["entity_id", "alias_name"],
    )
    op.create_unique_constraint(
        "uq_causal_edges_cause_effect_label",
        "causal_edges",
        ["cause_event_id", "effect_event_id", "relationship_label"],
    )
    op.create_unique_constraint(
        "uq_moat_metric_snapshots_date",
        "moat_metric_snapshots",
        ["snapshot_date"],
    )


def downgrade() -> None:
    # Drop unique constraints
    op.drop_constraint(
        "uq_moat_metric_snapshots_date", "moat_metric_snapshots", type_="unique"
    )
    op.drop_constraint(
        "uq_causal_edges_cause_effect_label", "causal_edges", type_="unique"
    )
    op.drop_constraint(
        "uq_entity_aliases_entity_alias", "entity_aliases", type_="unique"
    )
    op.drop_constraint(
        "uq_ml_model_registry_name_version", "ml_model_registry", type_="unique"
    )
    op.drop_constraint(
        "uq_signal_scores_signal_type", "signal_scores", type_="unique"
    )

    # Drop indexes
    op.drop_index("ix_regulatory_impacts_recorded_by", table_name="regulatory_impacts")
    op.drop_index("ix_regulatory_rules_created_by", table_name="regulatory_rules")
    op.drop_index(
        "ix_regulatory_events_created_by", table_name="regulatory_events"
    )
    op.drop_index(
        "ix_regulatory_events_source_event_id", table_name="regulatory_events"
    )
    op.drop_index(
        "ix_regulatory_events_source_signal_id", table_name="regulatory_events"
    )
    op.drop_index("ix_credit_transactions_user_id", table_name="credit_transactions")
    op.drop_index("ix_ai_jobs_user_id", table_name="ai_jobs")
    op.drop_index("ix_regulatory_impacts_entity_id", table_name="regulatory_impacts")
    op.drop_index("ix_regulatory_impacts_rule_id", table_name="regulatory_impacts")
    op.drop_index("ix_regulatory_impacts_event_id", table_name="regulatory_impacts")
    op.drop_index("ix_regulatory_rules_event_id", table_name="regulatory_rules")

    # Drop FK constraints
    op.drop_constraint(
        "fk_ai_usage_logs_org_id", "ai_usage_logs", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_ai_usage_logs_user_id", "ai_usage_logs", type_="foreignkey"
    )
