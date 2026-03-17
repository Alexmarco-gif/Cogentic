"""Add market_data_points table for time-series price/rate tracking.

Stores structured numeric data extracted by NER for trend analysis:
  - Commodity prices (rice ₦/bag, crude oil $/barrel)
  - Forex rates (NGN/USD parallel, EGP/USD)
  - Interest rates, inflation figures, index values
  - Volume data (trade volumes, production tonnage)

Enables "was ₦X, now ₦Y" reasoning instead of just raw signal text.

Revision ID: 2026_03_05_0002
Revises: 2026_03_05_0001
Create Date: 2026-03-05 00:02:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_03_05_0002"
down_revision: Union[str, None] = "2026_03_05_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_data_points",
        # PK
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        # Core value
        sa.Column(
            "metric",
            sa.String(200),
            nullable=False,
            index=True,
            comment="Normalized metric name (e.g. rice_price, ngn_usd_parallel)",
        ),
        sa.Column(
            "value", sa.Float, nullable=False, comment="Numeric value of the data point"
        ),
        sa.Column(
            "unit",
            sa.String(50),
            nullable=False,
            comment="Unit of measurement (NGN/50kg, USD/barrel, percent)",
        ),
        sa.Column(
            "currency",
            sa.String(3),
            nullable=True,
            comment="ISO 4217 currency code if applicable",
        ),
        # Temporal
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            index=True,
            comment="When this data point was observed/published",
        ),
        # Source linkage
        sa.Column(
            "signal_id",
            UUID(as_uuid=True),
            sa.ForeignKey("signals.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="Signal this data point was extracted from",
        ),
        sa.Column(
            "entity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="Entity this data point relates to",
        ),
        # Geography
        sa.Column(
            "country_code",
            sa.String(3),
            nullable=True,
            index=True,
            comment="ISO 3166-1 alpha-3 country code",
        ),
        sa.Column(
            "region",
            sa.String(100),
            nullable=True,
            comment="State/region/market location",
        ),
        # Context
        sa.Column("context", sa.Text, nullable=True, comment="Brief surrounding text"),
        sa.Column(
            "confidence",
            sa.Float,
            nullable=False,
            server_default="0.8",
            comment="Extraction confidence (0-1)",
        ),
        sa.Column(
            "metadata", JSONB, nullable=True, comment="Additional structured metadata"
        ),
        # Timestamps
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

    # Composite indexes for time-series queries
    op.create_index(
        "ix_market_data_metric_observed",
        "market_data_points",
        ["metric", "observed_at"],
    )
    op.create_index(
        "ix_market_data_entity",
        "market_data_points",
        ["entity_id", "metric", "observed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_market_data_entity", table_name="market_data_points")
    op.drop_index("ix_market_data_metric_observed", table_name="market_data_points")
    op.drop_table("market_data_points")
