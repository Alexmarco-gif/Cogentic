"""create pricing config table

Revision ID: 2026_02_15_0006
Revises: 2026_02_15_0005
Create Date: 2026-02-15 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '2026_02_15_0006'
down_revision: Union[str, None] = '2026_02_15_0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pricing_config',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('config_key', sa.String(100), unique=True, nullable=False),
        sa.Column('config_value', JSONB, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('updated_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    )


def downgrade() -> None:
    op.drop_table('pricing_config')
