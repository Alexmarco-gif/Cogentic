"""Add AI usage tracking table

Revision ID: 2026_02_12_0001
Revises: 2026_02_11_0001
Create Date: 2026-02-12 14:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "2026_02_12_0001"
down_revision = "2026_02_11_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add AI usage tracking table for cost monitoring."""
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("org_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("total_tokens", sa.Integer(), nullable=False, default=0),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, default=0.0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Indexes for analytics queries
    op.create_index(
        "ix_ai_usage_logs_created_at",
        "ai_usage_logs",
        ["created_at"],
    )
    op.create_index(
        "ix_ai_usage_logs_org_created",
        "ai_usage_logs",
        ["org_id", "created_at"],
    )
    op.create_index(
        "ix_ai_usage_logs_operation",
        "ai_usage_logs",
        ["operation"],
    )


def downgrade() -> None:
    """Remove AI usage tracking table."""
    op.drop_index("ix_ai_usage_logs_operation")
    op.drop_index("ix_ai_usage_logs_org_created")
    op.drop_index("ix_ai_usage_logs_created_at")
    op.drop_table("ai_usage_logs")
