"""Add influence_snapshots table for temporal influence tracking.

Stores periodic influence score measurements for entities so the system
can track influence trends over time.

Revision ID: 2026_02_25_0002
Revises: 2026_02_26_0001
Create Date: 2026-02-25 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_02_25_0002"
down_revision: Union[str, None] = "2026_02_26_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "influence_snapshots",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "entity_id",
            UUID(as_uuid=True),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("influence_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("pagerank", sa.Float, nullable=False, server_default="0"),
        sa.Column("betweenness", sa.Float, nullable=False, server_default="0"),
        sa.Column("eigenvector", sa.Float, nullable=False, server_default="0"),
        sa.Column("degree", sa.Float, nullable=False, server_default="0"),
        sa.Column("closeness", sa.Float, nullable=False, server_default="0"),
        sa.Column("network_size", sa.Integer, nullable=True),
        sa.Column("direct_connections", sa.Integer, nullable=True),
        sa.Column(
            "industry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("industries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Indexes for efficient time-series queries
    op.create_index(
        "ix_influence_snapshots_entity_id",
        "influence_snapshots",
        ["entity_id"],
    )
    op.create_index(
        "ix_influence_snapshots_snapshot_date",
        "influence_snapshots",
        ["snapshot_date"],
    )
    op.create_index(
        "ix_influence_snapshots_industry_id",
        "influence_snapshots",
        ["industry_id"],
    )
    # Composite index for the most common query pattern
    op.create_index(
        "ix_influence_snapshots_entity_date",
        "influence_snapshots",
        ["entity_id", "snapshot_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_influence_snapshots_entity_date")
    op.drop_index("ix_influence_snapshots_industry_id")
    op.drop_index("ix_influence_snapshots_snapshot_date")
    op.drop_index("ix_influence_snapshots_entity_id")
    op.drop_table("influence_snapshots")
