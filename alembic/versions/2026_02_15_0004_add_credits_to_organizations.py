"""add credits to organizations

Revision ID: 2026_02_15_0004
Revises: 2026_02_15_0003
Create Date: 2026-02-15 10:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_02_15_0004'
down_revision: Union[str, None] = '2026_02_15_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add credit-related columns
    op.add_column('organizations', sa.Column('credits_allocated_monthly', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('organizations', sa.Column('credits_consumed', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('organizations', sa.Column('credits_overage_rate', sa.Numeric(10, 2), nullable=False, server_default='0.10'))


def downgrade() -> None:
    op.drop_column('organizations', 'credits_overage_rate')
    op.drop_column('organizations', 'credits_consumed')
    op.drop_column('organizations', 'credits_allocated_monthly')
