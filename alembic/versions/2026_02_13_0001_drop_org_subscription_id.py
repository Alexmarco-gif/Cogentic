"""Drop dead subscription_id column from organizations

Revision ID: drop_org_sub_id
Revises: None (apply after latest head)
Create Date: 2026-02-13

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "drop_org_sub_id"
down_revision: Union[str, None] = None  # Set to current head before running
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("organizations", "subscription_id")


def downgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("subscription_id", PGUUID(as_uuid=True), nullable=True),
    )
