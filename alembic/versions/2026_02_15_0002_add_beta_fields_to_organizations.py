"""add beta fields to organizations

Revision ID: 2026_02_15_0002
Revises: 2026_02_15_0001
Create Date: 2026-02-15 10:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_02_15_0002'
down_revision: Union[str, None] = '2026_02_15_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {
        column["name"] for column in inspector.get_columns("organizations")
    }
    existing_indexes = {
        index["name"] for index in inspector.get_indexes("organizations")
    }

    # Add beta-related columns only if they are missing.
    if "is_beta_account" not in existing_columns:
        op.add_column(
            "organizations",
            sa.Column(
                "is_beta_account",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
    if "beta_start_date" not in existing_columns:
        op.add_column(
            "organizations",
            sa.Column("beta_start_date", sa.DateTime(timezone=True), nullable=True),
        )
    if "beta_end_date" not in existing_columns:
        op.add_column(
            "organizations",
            sa.Column("beta_end_date", sa.DateTime(timezone=True), nullable=True),
        )
    if "beta_discount_percent" not in existing_columns:
        op.add_column(
            "organizations",
            sa.Column(
                "beta_discount_percent",
                sa.Numeric(5, 2),
                nullable=False,
                server_default=sa.text("50.00"),
            ),
        )

    # Create index for beta status queries only if missing.
    if "idx_organizations_beta_status" not in existing_indexes:
        op.create_index(
            "idx_organizations_beta_status",
            "organizations",
            ["is_beta_account", "beta_end_date"],
        )


def downgrade() -> None:
    op.drop_index('idx_organizations_beta_status', 'organizations')
    op.drop_column('organizations', 'beta_discount_percent')
    op.drop_column('organizations', 'beta_end_date')
    op.drop_column('organizations', 'beta_start_date')
    op.drop_column('organizations', 'is_beta_account')
