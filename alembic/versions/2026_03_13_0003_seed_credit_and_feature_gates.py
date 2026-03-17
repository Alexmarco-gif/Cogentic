"""Seed missing and new feature gates.

Adds 5 feature gate rows:
  - intelligence_briefs      (growth)     — was missing; routes used it but DB row absent
  - bulk_document_operations (mid_market) — was missing; same issue
  - situation_room           (growth)     — new
  - marketplace_subscribe    (growth)     — new
  - market_data              (mid_market) — new

Revision ID: 2026_03_13_0003
Revises: 2026_03_13_0002
Create Date: 2026-03-13 00:03:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "2026_03_13_0003"
down_revision: Union[str, None] = "2026_03_13_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
        INSERT INTO feature_gates
            (feature_key, required_tier, required_role, is_enterprise_only, description)
        VALUES
        ('intelligence_briefs',      'growth',     NULL, FALSE, 'Intelligence brief generation and regeneration'),
        ('bulk_document_operations', 'mid_market', NULL, FALSE, 'Bulk document upload and processing'),
        ('situation_room',           'growth',     NULL, FALSE, 'Live situation room dashboard and WebSocket feed'),
        ('marketplace_subscribe',    'growth',     NULL, FALSE, 'Subscribe to signal marketplace templates'),
        ('market_data',              'mid_market', NULL, FALSE, 'Market data time-series access')
        ON CONFLICT (feature_key) DO NOTHING
    """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM feature_gates WHERE feature_key IN ("
            "'intelligence_briefs', 'bulk_document_operations', "
            "'situation_room', 'marketplace_subscribe', 'market_data')"
        )
    )
