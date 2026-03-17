"""seed feature gates data

Revision ID: 2026_02_15_0010
Revises: 2026_02_15_0009
Create Date: 2026-02-15 10:09:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_02_15_0010"
down_revision: Union[str, None] = "2026_02_15_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
        INSERT INTO feature_gates
            (feature_key, required_tier, required_role, is_enterprise_only, description)
        VALUES
        ('continuous_signals_limited', 'explorer',   NULL, FALSE, 'Limited continuous signals access (50/month)'),
        ('continuous_signals_full',    'growth',     NULL, FALSE, 'Full continuous signals access'),
        ('on_demand_synthesis',        'growth',     NULL, FALSE, 'On-demand synthesis capability'),
        ('api_access',                 'growth',     NULL, FALSE, 'API access enabled'),
        ('compliance_modules',         'mid_market', NULL, FALSE, 'Compliance module access'),
        ('custom_contracts',           'mid_market', NULL, FALSE, 'Custom contract creation'),
        ('private_signal_store',       'enterprise', NULL, TRUE,  'Private signal store access')
        ON CONFLICT (feature_key) DO NOTHING
    """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM feature_gates WHERE feature_key IN ("
            "'continuous_signals_limited', 'continuous_signals_full', 'on_demand_synthesis',"
            " 'api_access', 'compliance_modules', 'custom_contracts', 'private_signal_store')"
        )
    )
