"""create beta accounts table

Revision ID: 2026_02_15_0007
Revises: 2026_02_15_0006
Create Date: 2026-02-15 10:06:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '2026_02_15_0007'
down_revision: Union[str, None] = '2026_02_15_0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'beta_accounts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('beta_start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('beta_end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('discount_percent', sa.Numeric(5, 2), nullable=False, server_default='50.00'),
        sa.Column('notified_14d_before', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notified_7d_before', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('transitioned_to_standard', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    
    # Create index for beta expiry queries
    op.create_index(
        'idx_beta_expiry',
        'beta_accounts',
        ['beta_end_date'],
        postgresql_where=sa.text('transitioned_to_standard = false')
    )


def downgrade() -> None:
    op.drop_index('idx_beta_expiry', 'beta_accounts')
    op.drop_table('beta_accounts')
