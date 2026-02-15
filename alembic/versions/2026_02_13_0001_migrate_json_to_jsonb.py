"""Migrate JSON columns to JSONB for GIN index support

Revision ID: migrate_json_to_jsonb
Revises: 2026_02_14_0001
Create Date: 2026-02-13

"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "migrate_json_jsonb"
down_revision: Union[str, None] = "2026_02_14_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alter column types from JSON to JSONB (lossless cast)
    op.execute(
        "ALTER TABLE signals ALTER COLUMN extracted_data TYPE JSONB USING extracted_data::jsonb"
    )
    op.execute(
        "ALTER TABLE signal_contracts ALTER COLUMN extraction_config TYPE JSONB USING extraction_config::jsonb"
    )
    op.execute(
        "ALTER TABLE entities ALTER COLUMN metadata TYPE JSONB USING metadata::jsonb"
    )
    op.execute(
        "ALTER TABLE industries ALTER COLUMN metadata TYPE JSONB USING metadata::jsonb"
    )
    op.execute(
        "ALTER TABLE intelligence_briefs ALTER COLUMN body_json TYPE JSONB USING body_json::jsonb"
    )
    op.execute(
        "ALTER TABLE chat_messages ALTER COLUMN sources_json TYPE JSONB USING sources_json::jsonb"
    )
    op.execute(
        "ALTER TABLE search_queries ALTER COLUMN results_json TYPE JSONB USING results_json::jsonb"
    )
    op.execute(
        "ALTER TABLE ml_model_runs ALTER COLUMN output_json TYPE JSONB USING output_json::jsonb"
    )
    op.execute(
        "ALTER TABLE ml_model_registry ALTER COLUMN metrics TYPE JSONB USING metrics::jsonb"
    )
    op.execute(
        "ALTER TABLE ai_jobs ALTER COLUMN input_params TYPE JSONB USING input_params::jsonb"
    )
    op.execute("ALTER TABLE ai_jobs ALTER COLUMN result TYPE JSONB USING result::jsonb")
    op.execute(
        "ALTER TABLE subscriptions ALTER COLUMN usage_current_period TYPE JSONB USING usage_current_period::jsonb"
    )
    op.execute(
        "ALTER TABLE audit_logs ALTER COLUMN changes TYPE JSONB USING changes::jsonb"
    )
    op.execute(
        "ALTER TABLE audit_logs ALTER COLUMN metadata TYPE JSONB USING metadata::jsonb"
    )
    op.execute(
        "ALTER TABLE organizations ALTER COLUMN settings TYPE JSONB USING settings::jsonb"
    )
    op.execute(
        "ALTER TABLE documents ALTER COLUMN shared_with TYPE JSONB USING shared_with::jsonb"
    )


def downgrade() -> None:
    # Revert JSONB back to JSON (lossless)
    op.execute(
        "ALTER TABLE signals ALTER COLUMN extracted_data TYPE JSON USING extracted_data::json"
    )
    op.execute(
        "ALTER TABLE signal_contracts ALTER COLUMN extraction_config TYPE JSON USING extraction_config::json"
    )
    op.execute(
        "ALTER TABLE entities ALTER COLUMN metadata TYPE JSON USING metadata::json"
    )
    op.execute(
        "ALTER TABLE industries ALTER COLUMN metadata TYPE JSON USING metadata::json"
    )
    op.execute(
        "ALTER TABLE intelligence_briefs ALTER COLUMN body_json TYPE JSON USING body_json::json"
    )
    op.execute(
        "ALTER TABLE chat_messages ALTER COLUMN sources_json TYPE JSON USING sources_json::json"
    )
    op.execute(
        "ALTER TABLE search_queries ALTER COLUMN results_json TYPE JSON USING results_json::json"
    )
    op.execute(
        "ALTER TABLE ml_model_runs ALTER COLUMN output_json TYPE JSON USING output_json::json"
    )
    op.execute(
        "ALTER TABLE ml_model_registry ALTER COLUMN metrics TYPE JSON USING metrics::json"
    )
    op.execute(
        "ALTER TABLE ai_jobs ALTER COLUMN input_params TYPE JSON USING input_params::json"
    )
    op.execute("ALTER TABLE ai_jobs ALTER COLUMN result TYPE JSON USING result::json")
    op.execute(
        "ALTER TABLE subscriptions ALTER COLUMN usage_current_period TYPE JSON USING usage_current_period::json"
    )
    op.execute(
        "ALTER TABLE audit_logs ALTER COLUMN changes TYPE JSON USING changes::json"
    )
    op.execute(
        "ALTER TABLE audit_logs ALTER COLUMN metadata TYPE JSON USING metadata::json"
    )
    op.execute(
        "ALTER TABLE organizations ALTER COLUMN settings TYPE JSON USING settings::json"
    )
    op.execute(
        "ALTER TABLE documents ALTER COLUMN shared_with TYPE JSON USING shared_with::json"
    )
