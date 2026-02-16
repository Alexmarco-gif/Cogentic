"""seed pricing config data

Revision ID: 2026_02_15_0009
Revises: 2026_02_15_0008
Create Date: 2026-02-15 10:08:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = '2026_02_15_0009'
down_revision: Union[str, None] = '2026_02_15_0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a representation of the pricing_config table
    pricing_config = table(
        'pricing_config',
        column('config_key', sa.String),
        column('config_value', sa.dialects.postgresql.JSONB)
    )
    
    # Insert pricing configuration data
    op.bulk_insert(
        pricing_config,
        [
            {'config_key': 'global_pricing_mode', 'config_value': '"beta"'},
            {'config_key': 'standard_price_explorer', 'config_value': '0'},
            {'config_key': 'standard_price_growth', 'config_value': '499'},
            {'config_key': 'standard_price_mid_market', 'config_value': '2499'},
            {'config_key': 'standard_price_enterprise', 'config_value': '9999'},
            {'config_key': 'trial_duration_days', 'config_value': '30'},
            {'config_key': 'trial_credits', 'config_value': '10000'},
        ]
    )


def downgrade() -> None:
    # Delete all seeded pricing config data
    op.execute("DELETE FROM pricing_config WHERE config_key IN ('global_pricing_mode', 'standard_price_explorer', 'standard_price_growth', 'standard_price_mid_market', 'standard_price_enterprise', 'trial_duration_days', 'trial_credits')")
