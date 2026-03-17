"""Migrate JSON columns to JSONB for GIN index support

Revision ID: d4e5f6a7b8c9
Create Date: 2026-02-13 10:30:00.000000

NOTE: Models already use JSONB. This migration converts any existing
JSON-typed columns in the database to JSONB to match the model definitions.
"""

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3f8a1b2d4e5"
branch_labels = None
depends_on = None


# Columns to migrate: (table_name, column_name)
COLUMNS_TO_MIGRATE = [
    ("signals", "extracted_data"),
    ("signal_contracts", "extraction_config"),
    ("entities", "metadata"),  # extra_data mapped to 'metadata' column
    ("industries", "metadata"),  # extra_data mapped to 'metadata' column
    ("intelligence_briefs", "body_json"),
    ("chat_messages", "sources_json"),
    ("search_queries", "results_json"),
    ("ml_model_runs", "output_json"),
    ("ml_model_registry", "metrics"),
    ("ai_jobs", "input_params"),
    ("ai_jobs", "result"),
    ("subscriptions", "usage_current_period"),
    ("audit_logs", "changes"),
    ("audit_logs", "metadata"),  # extra_data mapped to 'metadata' column
    ("organizations", "settings"),
    ("documents", "shared_with"),
]


def upgrade() -> None:
    for table, column in COLUMNS_TO_MIGRATE:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE JSONB USING {column}::jsonb"
        )


def downgrade() -> None:
    for table, column in COLUMNS_TO_MIGRATE:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE JSON USING {column}::json"
        )
