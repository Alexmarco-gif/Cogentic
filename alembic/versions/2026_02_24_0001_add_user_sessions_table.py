"""Add user_sessions table.

Tracks authenticated sessions per-device without needing Auth0's paid
Sessions Management add-on.

Revision ID: 2026_02_24_0001
Revises: 2026_02_17_0001
Create Date: 2026-02-24 00:01:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_02_24_0001"
down_revision: Union[str, None] = "2026_02_17_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("device", sa.String(255), nullable=False, server_default="Unknown"),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index(
        "ix_user_sessions_user_id_last_active",
        "user_sessions",
        ["user_id", "last_active_at"],
    )
    # Unique constraint: one session record per (user, ip, device) combo
    op.create_index(
        "uq_user_sessions_user_ip_device",
        "user_sessions",
        ["user_id", "ip_address", "device"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_user_sessions_user_ip_device", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id_last_active", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
