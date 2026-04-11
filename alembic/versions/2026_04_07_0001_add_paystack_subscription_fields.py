"""Add Paystack billing fields to subscriptions.

Revision ID: 2026_04_07_0001
Revises: 2026_03_24_0001
Create Date: 2026-04-07 00:01:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "2026_04_07_0001"
down_revision: Union[str, None] = "2026_03_24_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("provider", sa.String(length=50), nullable=True))
    op.add_column(
        "subscriptions",
        sa.Column("provider_customer_code", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("provider_plan_code", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("provider_subscription_code", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("provider_email_token", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("latest_reference", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("authorization_code", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "provider_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.create_index(
        "ix_subscriptions_provider", "subscriptions", ["provider"], unique=False
    )
    op.create_index(
        "ix_subscriptions_provider_plan_code",
        "subscriptions",
        ["provider_plan_code"],
        unique=False,
    )
    op.create_index(
        "ix_subscriptions_latest_reference",
        "subscriptions",
        ["latest_reference"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_subscriptions_provider_customer_code",
        "subscriptions",
        ["provider_customer_code"],
    )
    op.create_unique_constraint(
        "uq_subscriptions_provider_subscription_code",
        "subscriptions",
        ["provider_subscription_code"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_subscriptions_provider_subscription_code",
        "subscriptions",
        type_="unique",
    )
    op.drop_constraint(
        "uq_subscriptions_provider_customer_code",
        "subscriptions",
        type_="unique",
    )
    op.drop_index("ix_subscriptions_latest_reference", table_name="subscriptions")
    op.drop_index("ix_subscriptions_provider_plan_code", table_name="subscriptions")
    op.drop_index("ix_subscriptions_provider", table_name="subscriptions")

    op.drop_column("subscriptions", "provider_metadata")
    op.drop_column("subscriptions", "authorization_code")
    op.drop_column("subscriptions", "latest_reference")
    op.drop_column("subscriptions", "provider_email_token")
    op.drop_column("subscriptions", "provider_subscription_code")
    op.drop_column("subscriptions", "provider_plan_code")
    op.drop_column("subscriptions", "provider_customer_code")
    op.drop_column("subscriptions", "provider")
