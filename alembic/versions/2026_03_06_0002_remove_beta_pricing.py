"""Remove beta pricing — drop beta_accounts table and beta columns from organizations.

Revision ID: 2026_03_06_0002
Revises: 2026_03_06_0001
Create Date: 2026-03-06 00:02:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "2026_03_06_0002"
down_revision: Union[str, None] = "2026_03_06_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop beta_accounts table (and its index)
    op.drop_index("idx_beta_expiry", table_name="beta_accounts", if_exists=True)
    op.drop_table("beta_accounts")

    # 2. Drop beta columns from organizations
    op.drop_column("organizations", "is_beta_account")
    op.drop_column("organizations", "beta_start_date")
    op.drop_column("organizations", "beta_end_date")
    op.drop_column("organizations", "beta_discount_percent")

    # 3. Switch global pricing mode to standard
    op.execute(
        sa.text(
            "UPDATE pricing_config SET config_value = '\"standard\"'::jsonb "
            "WHERE config_key = 'global_pricing_mode'"
        )
    )


def downgrade() -> None:
    # 1. Restore global_pricing_mode to beta
    op.execute(
        sa.text(
            "UPDATE pricing_config SET config_value = '\"beta\"'::jsonb "
            "WHERE config_key = 'global_pricing_mode'"
        )
    )

    # 2. Restore beta columns on organizations
    op.add_column(
        "organizations",
        sa.Column(
            "beta_discount_percent",
            sa.Numeric(5, 2),
            nullable=True,
            server_default="50.00",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column("beta_end_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("beta_start_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "is_beta_account", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.create_index(
        "ix_organizations_is_beta_account",
        "organizations",
        ["is_beta_account"],
    )

    # 3. Recreate beta_accounts table
    op.create_table(
        "beta_accounts",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("beta_start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("beta_end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "discount_percent", sa.Numeric(5, 2), nullable=False, server_default="50.00"
        ),
        sa.Column(
            "notified_14d_before", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "notified_7d_before", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "transitioned_to_standard",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_beta_expiry",
        "beta_accounts",
        ["beta_end_date"],
        postgresql_where=sa.text("transitioned_to_standard = false"),
    )
