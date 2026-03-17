"""Add missing foreign key constraints to regulatory tables

Revision ID: c3f8a1b2d4e5
Revises: 2026_02_14_0001_add_regulatory_knowledge_tables
Create Date: 2026-02-13 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "c3f8a1b2d4e5"
down_revision = "b8c67c37fee0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    def _fk_exists(table_name: str, fk_name: str) -> bool:
        """Check if a foreign key constraint already exists."""
        fks = inspector.get_foreign_keys(table_name)
        return any(fk.get("name") == fk_name for fk in fks)

    # RegulatoryEvent.source_signal_id -> signals.id
    if not _fk_exists("regulatory_events", "fk_regulatory_events_source_signal_id"):
        op.create_foreign_key(
            "fk_regulatory_events_source_signal_id",
            "regulatory_events",
            "signals",
            ["source_signal_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # RegulatoryEvent.created_by -> users.id
    if not _fk_exists("regulatory_events", "fk_regulatory_events_created_by"):
        op.create_foreign_key(
            "fk_regulatory_events_created_by",
            "regulatory_events",
            "users",
            ["created_by"],
            ["id"],
            ondelete="SET NULL",
        )

    # RegulatoryRule.created_by -> users.id
    if not _fk_exists("regulatory_rules", "fk_regulatory_rules_created_by"):
        op.create_foreign_key(
            "fk_regulatory_rules_created_by",
            "regulatory_rules",
            "users",
            ["created_by"],
            ["id"],
            ondelete="SET NULL",
        )

    # RegulatoryImpact.rule_id -> regulatory_rules.id
    if not _fk_exists("regulatory_impacts", "fk_regulatory_impacts_rule_id"):
        op.create_foreign_key(
            "fk_regulatory_impacts_rule_id",
            "regulatory_impacts",
            "regulatory_rules",
            ["rule_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # RegulatoryImpact.entity_id -> entities.id
    if not _fk_exists("regulatory_impacts", "fk_regulatory_impacts_entity_id"):
        op.create_foreign_key(
            "fk_regulatory_impacts_entity_id",
            "regulatory_impacts",
            "entities",
            ["entity_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # RegulatoryImpact.recorded_by -> users.id
    if not _fk_exists("regulatory_impacts", "fk_regulatory_impacts_recorded_by"):
        op.create_foreign_key(
            "fk_regulatory_impacts_recorded_by",
            "regulatory_impacts",
            "users",
            ["recorded_by"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    op.drop_constraint(
        "fk_regulatory_impacts_recorded_by", "regulatory_impacts", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_regulatory_impacts_entity_id", "regulatory_impacts", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_regulatory_impacts_rule_id", "regulatory_impacts", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_regulatory_rules_created_by", "regulatory_rules", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_regulatory_events_created_by", "regulatory_events", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_regulatory_events_source_signal_id", "regulatory_events", type_="foreignkey"
    )
