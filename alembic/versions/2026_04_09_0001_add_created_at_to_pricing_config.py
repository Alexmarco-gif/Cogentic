"""Add created_at to pricing_config if missing.

Revision ID: 2026_04_09_0001
Revises: 2026_04_07_0001
Create Date: 2026-04-09 18:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "2026_04_09_0001"
down_revision: Union[str, None] = "2026_04_07_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("pricing_config")}

    if "created_at" not in columns:
        op.add_column(
            "pricing_config",
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
        )
        op.execute(
            sa.text(
                """
                UPDATE pricing_config
                SET created_at = COALESCE(created_at, updated_at, NOW())
                WHERE created_at IS NULL
                """
            )
        )
        op.alter_column("pricing_config", "created_at", nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("pricing_config")}

    if "created_at" in columns:
        op.drop_column("pricing_config", "created_at")
