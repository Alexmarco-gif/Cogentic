"""Add UNIQUE(contract_id, content_hash) constraint on signals table.

Prevents concurrent signal fetchers from inserting duplicate signals
for the same contract + content hash combination.

Revision ID: 2026_03_13_0001
Revises: 2026_03_07_0001
Create Date: 2026-03-13 00:01:00.000000
"""

from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "2026_03_13_0001"
down_revision: Union[str, None] = "2026_03_07_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove any existing duplicate rows before enforcing the constraint.
    # We keep the row with the lowest created_at (earliest ingested copy).
    op.execute(
        """
        DELETE FROM signals
        WHERE id NOT IN (
            SELECT DISTINCT ON (contract_id, content_hash) id
            FROM signals
            WHERE content_hash IS NOT NULL
            ORDER BY contract_id, content_hash, created_at ASC
        )
        AND content_hash IS NOT NULL
        """
    )

    op.create_index(
        "uq_signals_contract_content_hash",
        "signals",
        ["contract_id", "content_hash"],
        unique=True,
        postgresql_where=sa.text("content_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_signals_contract_content_hash", table_name="signals")
