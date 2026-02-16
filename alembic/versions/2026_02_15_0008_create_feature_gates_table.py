"""create feature gates table

Revision ID: 2026_02_15_0008
Revises: 2026_02_15_0007
Create Date: 2026-02-15 10:07:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_02_15_0008'
down_revision: Union[str, None] = '2026_02_15_0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'feature_gates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('feature_key', sa.String(100), unique=True, nullable=False),
        sa.Column('required_tier', sa.String(50), nullable=False),
        sa.Column('required_role', sa.String(50), nullable=True),
        sa.Column('is_enterprise_only', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('feature_gates')
