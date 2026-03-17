"""Merge agriculture and regulatory branches.

Revision ID: b8c67c37fee0
Revises: 2026_02_12_0003, 2026_02_14_0001
Create Date: 2026-02-12 13:20:00.000000

"""

from collections.abc import Sequence
from typing import Union

# revision identifiers, used by Alembic.
revision: str = "b8c67c37fee0"
down_revision: Union[str, None] = ("2026_02_12_0003", "2026_02_14_0001")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
