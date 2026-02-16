"""add trial fields to organizations

Revision ID: 2026_02_15_0003
Revises: 2026_02_15_0002
Create Date: 2026-02-15 10:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_02_15_0003'
down_revision: Union[str, None] = '2026_02_15_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add trial-related columns
    op.add_column('organizations', sa.Column('trial_status', sa.String(50), nullable=False, server_default='active'))
    op.add_column('organizations', sa.Column('trial_start_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('organizations', sa.Column('trial_end_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('organizations', sa.Column('billing_cycle_start', sa.Date(), nullable=True))
    
    # Create index for trial status queries
    op.create_index('idx_organizations_trial_status', 'organizations', ['trial_status', 'trial_end_date'])


def downgrade() -> None:
    op.drop_index('idx_organizations_trial_status', 'organizations')
    op.drop_column('organizations', 'billing_cycle_start')
    op.drop_column('organizations', 'trial_end_date')
    op.drop_column('organizations', 'trial_start_date')
    op.drop_column('organizations', 'trial_status')
