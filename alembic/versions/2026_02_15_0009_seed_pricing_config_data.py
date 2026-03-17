"""seed pricing config data

Revision ID: 2026_02_15_0009
Revises: 2026_02_15_0008
Create Date: 2026-02-15 10:08:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_02_15_0009"
down_revision: Union[str, None] = "2026_02_15_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
        INSERT INTO pricing_config (config_key, config_value) VALUES
        ('global_pricing_mode',       '"beta"'::jsonb),
        ('standard_price_explorer',   '0'::jsonb),
        ('standard_price_growth',     '499'::jsonb),
        ('standard_price_mid_market', '2499'::jsonb),
        ('standard_price_enterprise', '9999'::jsonb),
        ('trial_duration_days',       '30'::jsonb),
        ('trial_credits',             '10000'::jsonb)
        ON CONFLICT (config_key) DO NOTHING
    """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM pricing_config WHERE config_key IN ("
            "'global_pricing_mode', 'standard_price_explorer', 'standard_price_growth',"
            " 'standard_price_mid_market', 'standard_price_enterprise',"
            " 'trial_duration_days', 'trial_credits')"
        )
    )
