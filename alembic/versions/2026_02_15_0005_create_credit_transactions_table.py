"""create credit transactions table

Revision ID: 2026_02_15_0005
Revises: 2026_02_15_0004
Create Date: 2026-02-15 10:04:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '2026_02_15_0005'
down_revision: Union[str, None] = '2026_02_15_0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'credit_transactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('credits_consumed', sa.Integer(), nullable=False),
        sa.Column('credits_remaining', sa.Integer(), nullable=False),
        sa.Column('metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    
    # Create indexes for efficient queries
    op.create_index('idx_credit_txn_org', 'credit_transactions', ['org_id', 'created_at'])
    op.create_index('idx_credit_txn_action', 'credit_transactions', ['action_type'])


def downgrade() -> None:
    op.drop_index('idx_credit_txn_action', 'credit_transactions')
    op.drop_index('idx_credit_txn_org', 'credit_transactions')
    op.drop_table('credit_transactions')
