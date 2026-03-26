"""Add org scoping to signal contracts and backfill existing tenant data.

Revision ID: 2026_03_24_0001
Revises: 2026_03_13_0003
Create Date: 2026-03-24 10:00:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "2026_03_24_0001"
down_revision: Union[str, None] = "2026_03_13_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UUID_REGEX = (
    "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-" "[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def upgrade() -> None:
    op.add_column(
        "signal_contracts",
        sa.Column("org_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_signal_contracts_org_id_organizations",
        "signal_contracts",
        "organizations",
        ["org_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_signal_contracts_org_id", "signal_contracts", ["org_id"])

    op.execute(
        sa.text(
            """
            UPDATE signal_contracts sc
            SET org_id = sts.org_id
            FROM signal_template_subscriptions sts
            WHERE sc.id = sts.contract_id
              AND sc.org_id IS NULL
              AND sts.org_id IS NOT NULL
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            UPDATE signal_contracts
            SET org_id = CAST(extraction_config->>'org_id' AS uuid)
            WHERE org_id IS NULL
              AND extraction_config ? 'org_id'
              AND extraction_config->>'org_id' ~* '{_UUID_REGEX}'
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE signals s
            SET org_id = sc.org_id
            FROM signal_contracts sc
            WHERE s.contract_id = sc.id
              AND s.org_id IS NULL
              AND sc.org_id IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_signal_contracts_org_id", table_name="signal_contracts")
    op.drop_constraint(
        "fk_signal_contracts_org_id_organizations",
        "signal_contracts",
        type_="foreignkey",
    )
    op.drop_column("signal_contracts", "org_id")
