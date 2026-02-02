"""change ip_address from inet to varchar

Revision ID: a762f3897625
Revises: 001
Create Date: 2026-01-30 06:54

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a762f3897625'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change ip_address column from INET to VARCHAR(45)
    op.execute("ALTER TABLE audit_logs ALTER COLUMN ip_address TYPE VARCHAR(45) USING ip_address::text")


def downgrade() -> None:
    # Change back to INET
    op.execute("ALTER TABLE audit_logs ALTER COLUMN ip_address TYPE INET USING ip_address::inet")
