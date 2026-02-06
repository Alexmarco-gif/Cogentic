"""initial schema with multi-tenant support and pgvector

Revision ID: 001
Revises:
Create Date: 2026-01-30 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension for embeddings (future AI features)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Organizations table (multi-tenant root)
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("billing_email", sa.String(255), nullable=True),
        sa.Column("settings", postgresql.JSONB, server_default="{}", nullable=False),
        sa.Column("max_users", sa.Integer, server_default="10", nullable=False),
        sa.Column("max_storage_gb", sa.Integer, server_default="10", nullable=False),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "data_region", sa.String(50), server_default="'us-east'", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_orgs_slug", "organizations", ["slug"])
    op.create_index(
        "idx_orgs_deleted",
        "organizations",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Users table (shadow profile from Auth0)
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("auth0_id", sa.String(255), unique=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("picture_url", sa.String(500), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("login_count", sa.Integer, server_default="0", nullable=False),
        sa.Column(
            "data_processing_consent",
            sa.Boolean,
            server_default="false",
            nullable=False,
        ),
        sa.Column("consent_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_users_auth0_id", "users", ["auth0_id"])
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index(
        "idx_users_deleted",
        "users",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Organization-User membership (many-to-many with RBAC)
    op.create_table(
        "org_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(50), server_default="'member'", nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("status", sa.String(50), server_default="'active'", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("org_id", "user_id", name="uq_org_user"),
    )
    op.create_index("idx_org_users_org", "org_users", ["org_id"])
    op.create_index("idx_org_users_user", "org_users", ["user_id"])
    op.create_index("idx_org_users_role", "org_users", ["org_id", "role"])

    # Documents table (user-uploaded files)
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("storage_path", sa.Text, nullable=True),
        sa.Column(
            "processing_status",
            sa.String(50),
            server_default="'pending'",
            nullable=False,
        ),
        sa.Column("extracted_text", sa.Text, nullable=True),
        sa.Column(
            "visibility", sa.String(50), server_default="'private'", nullable=False
        ),
        sa.Column("shared_with", postgresql.JSONB, server_default="[]", nullable=False),
        sa.Column("retention_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_docs_org", "documents", ["org_id"])
    op.create_index("idx_docs_owner", "documents", ["owner_id"])
    op.create_index("idx_docs_status", "documents", ["org_id", "processing_status"])
    op.create_index(
        "idx_docs_retention",
        "documents",
        ["retention_date"],
        postgresql_where=sa.text("retention_date IS NOT NULL"),
    )
    op.create_index(
        "idx_docs_deleted",
        "documents",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # AI Jobs table (async processing)
    op.create_table(
        "ai_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_type", sa.String(100), nullable=False),
        sa.Column(
            "input_params", postgresql.JSONB, server_default="{}", nullable=False
        ),
        sa.Column("status", sa.String(50), server_default="'queued'", nullable=False),
        sa.Column("priority", sa.Integer, server_default="0", nullable=False),
        sa.Column("attempts", sa.Integer, server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer, server_default="3", nullable=False),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_jobs_org", "ai_jobs", ["org_id"])
    op.create_index(
        "idx_jobs_status",
        "ai_jobs",
        ["status", "priority"],
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )
    op.create_index("idx_jobs_document", "ai_jobs", ["document_id"])
    op.create_index("idx_jobs_created", "ai_jobs", ["created_at"])

    # Subscriptions table (billing)
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), unique=True, nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), unique=True, nullable=True),
        sa.Column("plan_tier", sa.String(50), nullable=False),
        sa.Column("billing_cycle", sa.String(50), nullable=True),
        sa.Column("price_cents", sa.Integer, nullable=True),
        sa.Column("currency", sa.String(3), server_default="'USD'", nullable=False),
        sa.Column("status", sa.String(50), server_default="'active'", nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "usage_current_period",
            postgresql.JSONB,
            server_default="{}",
            nullable=False,
        ),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_subs_stripe_customer", "subscriptions", ["stripe_customer_id"])
    op.create_index("idx_subs_status", "subscriptions", ["status"])
    op.create_index("idx_subs_period_end", "subscriptions", ["current_period_end"])

    # Audit Logs table (immutable compliance trail)
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("request_id", sa.String(255), nullable=True),
        sa.Column("changes", postgresql.JSONB, nullable=True),
        sa.Column("metadata", postgresql.JSONB, server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "idx_audit_org", "audit_logs", ["org_id", sa.text("created_at DESC")]
    )
    op.create_index(
        "idx_audit_user", "audit_logs", ["user_id", sa.text("created_at DESC")]
    )
    op.create_index(
        "idx_audit_action", "audit_logs", ["action", sa.text("created_at DESC")]
    )
    op.create_index(
        "idx_audit_resource", "audit_logs", ["resource_type", "resource_id"]
    )

    # Make audit logs immutable (prevent UPDATE/DELETE)
    # Split into separate commands for asyncpg compatibility
    op.execute(
        "CREATE RULE audit_log_no_update AS ON UPDATE TO audit_logs DO INSTEAD NOTHING"
    )
    op.execute(
        "CREATE RULE audit_log_no_delete AS ON DELETE TO audit_logs DO INSTEAD NOTHING"
    )


def downgrade() -> None:
    # Drop rules first
    op.execute("DROP RULE IF EXISTS audit_log_no_update ON audit_logs")
    op.execute("DROP RULE IF EXISTS audit_log_no_delete ON audit_logs")

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("audit_logs")
    op.drop_table("subscriptions")
    op.drop_table("ai_jobs")
    op.drop_table("documents")
    op.drop_table("org_users")
    op.drop_table("users")
    op.drop_table("organizations")

    # Drop pgvector extension
    op.execute("DROP EXTENSION IF EXISTS vector")
