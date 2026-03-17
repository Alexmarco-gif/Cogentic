"""Merge heads after pricing and subscription cleanup.

Revision ID: 2026_02_16_0001
Revises: e5f6a7b8c9d0, 2026_02_15_0010
Create Date: 2026-02-16 00:01:00.000000

"""

from collections.abc import Sequence
from typing import Union

# revision identifiers, used by Alembic.
revision: str = "2026_02_16_0001"
down_revision: Union[str, None] = ("e5f6a7b8c9d0", "2026_02_15_0010")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
