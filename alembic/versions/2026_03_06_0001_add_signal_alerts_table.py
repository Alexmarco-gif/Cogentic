"""Add signal_alerts table for change detection and anomaly alerts.

Creates the signal_alerts table populated by the ChangeDetectionService
when MarketDataPoint values deviate significantly from rolling baselines.

Revision ID: 2026_03_06_0001
Revises: 2026_03_05_0002
Create Date: 2026-03-06 00:01:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "2026_03_06_0001"
down_revision = "2026_03_05_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signal_alerts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "signal_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("signals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "entity_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("metric", sa.String(200), nullable=True),
        sa.Column("country_code", sa.String(10), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("current_value", sa.Float, nullable=True),
        sa.Column("baseline_value", sa.Float, nullable=True),
        sa.Column("deviation_pct", sa.Float, nullable=True),
        sa.Column("acknowledged", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_signal_alerts_alert_type", "signal_alerts", ["alert_type"])
    op.create_index("ix_signal_alerts_severity", "signal_alerts", ["severity"])
    op.create_index("ix_signal_alerts_metric", "signal_alerts", ["metric"])
    op.create_index("ix_signal_alerts_country_code", "signal_alerts", ["country_code"])
    op.create_index("ix_signal_alerts_acknowledged", "signal_alerts", ["acknowledged"])
    op.create_index("ix_signal_alerts_signal_id", "signal_alerts", ["signal_id"])
    op.create_index("ix_signal_alerts_entity_id", "signal_alerts", ["entity_id"])


def downgrade() -> None:
    op.drop_table("signal_alerts")
