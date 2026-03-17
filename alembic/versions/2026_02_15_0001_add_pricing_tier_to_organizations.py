"""add pricing tier to organizations

Revision ID: 2026_02_15_0001
Revises: 2026_02_14_0001
Create Date: 2026-02-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_02_15_0001'
down_revision: Union[str, None] = '2026_02_14_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add pricing_tier column with default 'explorer'
    op.add_column('organizations', sa.Column('pricing_tier', sa.String(50), nullable=False, server_default='explorer'))
    
    # Create index for pricing_tier
    op.create_index('idx_organizations_pricing_tier', 'organizations', ['pricing_tier'])


def downgrade() -> None:
    op.drop_index('idx_organizations_pricing_tier', 'organizations')
    op.drop_column('organizations', 'pricing_tier')
