"""Fix moat_metric_snapshots.snapshot_date from VARCHAR to DATE.

The original migration (2026_02_12_0003) created this column as String(10).
Date comparisons, range queries, and ORDER BY on a varchar column behave
incorrectly. This migration converts the column to the proper DATE type.

The conversion is safe because all existing values are stored as ISO-8601
strings ('YYYY-MM-DD'), which Postgres can cast directly to DATE.

The upgrade is guarded: if the column is already DATE (e.g. on a fresh deploy
that got the fixed 2026_02_12_0003), it is a no-op.

Revision ID: 2026_02_25_0001
Revises: 2026_02_24_0001
Create Date: 2026-02-25 00:01:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_02_25_0001"
down_revision: Union[str, None] = "2026_02_24_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_data_type(conn: sa.engine.Connection, table: str, column: str) -> str:
    """Return the PostgreSQL data_type string for a given column."""
    result = conn.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "  AND table_name   = :tbl "
            "  AND column_name  = :col"
        ),
        {"tbl": table, "col": column},
    )
    row = result.fetchone()
    return row[0].lower() if row else ""


def upgrade() -> None:
    conn = op.get_bind()
    dtype = _column_data_type(conn, "moat_metric_snapshots", "snapshot_date")

    # Only alter if the column is still stored as a character type.
    # On a fresh deploy with the fixed 0003 migration it is already DATE — skip.
    if dtype in ("character varying", "varchar", "character", "text"):
        op.execute(
            sa.text(
                "ALTER TABLE moat_metric_snapshots "
                "ALTER COLUMN snapshot_date TYPE DATE "
                "USING snapshot_date::date"
            )
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE moat_metric_snapshots "
            "ALTER COLUMN snapshot_date TYPE VARCHAR(10) "
            "USING snapshot_date::text"
        )
    )
