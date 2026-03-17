"""Drop dead subscription_id column from organizations

Revision ID: e5f6a7b8c9d0
Create Date: 2026-02-13 11:00:00.000000

The subscription relationship works via Subscription.org_id, not
Organization.subscription_id. This column has no FK and is never populated.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("organizations", "subscription_id")


def downgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("subscription_id", PGUUID(as_uuid=True), nullable=True),
    )
