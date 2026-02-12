"""Add moat metrics snapshot table

Revision ID: 2026_02_12_0003
Revises: 2026_02_12_0002
Create Date: 2026-02-12

Stores periodic snapshots of intelligence moat success metrics:
  1. Entity Graph Coverage
  2. Causal Chains Discovered
  3. Prediction Accuracy
  4. Replicability Score
  5. User Retention (DAU/MAU)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers
revision = "2026_02_12_0003"
down_revision = "2026_02_12_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "moat_metric_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("snapshot_date", sa.String(10), nullable=False, index=True),
        # Metric 1: Entity Graph Coverage
        sa.Column("entity_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("entity_verified_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("entity_relationship_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("entity_source_profile_count", sa.Integer, nullable=False, server_default="0"),
        # Metric 2: Causal Chains
        sa.Column("causal_event_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("causal_edge_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("causal_chain_count", sa.Integer, nullable=False, server_default="0"),
        # Metric 3: Prediction Accuracy
        sa.Column("prediction_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("prediction_accurate", sa.Integer, nullable=False, server_default="0"),
        sa.Column("prediction_inaccurate", sa.Integer, nullable=False, server_default="0"),
        sa.Column("prediction_accuracy_pct", sa.Float, nullable=True),
        # Metric 4: Replicability Score
        sa.Column("replicability_tests_run", sa.Integer, nullable=False, server_default="0"),
        sa.Column("replicability_score_pct", sa.Float, nullable=True),
        # Metric 5: DAU/MAU
        sa.Column("dau", sa.Integer, nullable=False, server_default="0"),
        sa.Column("mau", sa.Integer, nullable=False, server_default="0"),
        sa.Column("dau_mau_ratio", sa.Float, nullable=True),
        # Overall
        sa.Column("moat_health_score", sa.Float, nullable=True),
        sa.Column("details", JSONB, nullable=False, server_default="{}"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("moat_metric_snapshots")
