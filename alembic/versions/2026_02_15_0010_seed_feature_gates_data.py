"""seed feature gates data

Revision ID: 2026_02_15_0010
Revises: 2026_02_15_0009
Create Date: 2026-02-15 10:09:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = '2026_02_15_0010'
down_revision: Union[str, None] = '2026_02_15_0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a representation of the feature_gates table
    feature_gates = table(
        'feature_gates',
        column('feature_key', sa.String),
        column('required_tier', sa.String),
        column('required_role', sa.String),
        column('is_enterprise_only', sa.Boolean),
        column('description', sa.Text)
    )
    
    # Insert feature gate definitions
    op.bulk_insert(
        feature_gates,
        [
            {
                'feature_key': 'continuous_signals_limited',
                'required_tier': 'explorer',
                'required_role': None,
                'is_enterprise_only': False,
                'description': 'Limited continuous signals access (50/month)'
            },
            {
                'feature_key': 'continuous_signals_full',
                'required_tier': 'growth',
                'required_role': None,
                'is_enterprise_only': False,
                'description': 'Full continuous signals access'
            },
            {
                'feature_key': 'on_demand_synthesis',
                'required_tier': 'growth',
                'required_role': None,
                'is_enterprise_only': False,
                'description': 'On-demand synthesis capability'
            },
            {
                'feature_key': 'api_access',
                'required_tier': 'growth',
                'required_role': None,
                'is_enterprise_only': False,
                'description': 'API access enabled'
            },
            {
                'feature_key': 'compliance_modules',
                'required_tier': 'mid_market',
                'required_role': None,
                'is_enterprise_only': False,
                'description': 'Compliance module access'
            },
            {
                'feature_key': 'custom_contracts',
                'required_tier': 'mid_market',
                'required_role': None,
                'is_enterprise_only': False,
                'description': 'Custom contract creation'
            },
            {
                'feature_key': 'private_signal_store',
                'required_tier': 'enterprise',
                'required_role': None,
                'is_enterprise_only': True,
                'description': 'Private signal store access'
            },
        ]
    )


def downgrade() -> None:
    # Delete all seeded feature gate data
    op.execute("DELETE FROM feature_gates WHERE feature_key IN ('continuous_signals_limited', 'continuous_signals_full', 'on_demand_synthesis', 'api_access', 'compliance_modules', 'custom_contracts', 'private_signal_store')")
