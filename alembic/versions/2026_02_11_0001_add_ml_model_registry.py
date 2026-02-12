"""Add ml_model_registry table

Revision ID: 2026_02_11_0001
Revises: 2026_02_10_0001
Create Date: 2026-02-11 08:00:00.000000+00:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2026_02_11_0001"
down_revision = "2026_02_10_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ml_model_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_name", sa.String(100), nullable=False, index=True),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("artifact_path", sa.Text, nullable=False),
        sa.Column("artifact_size_bytes", sa.Integer, nullable=True),
        sa.Column("metrics", sa.JSON, server_default="{}", nullable=False),
        sa.Column("status", sa.String(50), server_default="active", nullable=False, index=True),
        sa.Column("training_samples", sa.Integer, nullable=True),
        sa.Column("training_duration_ms", sa.Integer, nullable=True),
        sa.Column(
            "trained_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
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
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("ml_model_registry")
