"""Mako template for migration scripts"""

"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "600f4a29ec2b"
down_revision: Union[str, None] = "a762f3897625"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === INDEXES FOR PERFORMANCE ===
    # NOTE: Indexes on users(email), users(auth0_id), org_users(org_id),
    # org_users(user_id), documents(org_id), ai_jobs(org_id) already exist
    # from 001_initial_schema with idx_ prefix. Only add NEW indexes here.

    # Documents table - composite index for "my documents" queries (NEW)
    op.create_index(
        "ix_documents_owner_created", "documents", ["owner_id", "created_at"]
    )

    # AI Jobs table - composite index for queue processing (NEW)
    op.create_index("ix_ai_jobs_status_created", "ai_jobs", ["status", "created_at"])

    # Audit logs table - audit trail queries (NEW - no indexes in initial schema)
    op.create_index("ix_audit_logs_org_created", "audit_logs", ["org_id", "created_at"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index(
        "ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"]
    )

    # Subscriptions table - org lookup with unique constraint (NEW)
    op.create_index("ix_subscriptions_org_id", "subscriptions", ["org_id"], unique=True)

    # === UNIQUE CONSTRAINTS ===

    # Prevent duplicate org memberships
    op.create_unique_constraint(
        "uq_org_users_org_user", "org_users", ["org_id", "user_id"]
    )

    # === CHECK CONSTRAINTS ===

    # Ensure positive limits
    op.create_check_constraint(
        "ck_organizations_max_users_positive", "organizations", "max_users > 0"
    )
    op.create_check_constraint(
        "ck_organizations_max_storage_positive", "organizations", "max_storage_gb > 0"
    )

    # Valid document sizes
    op.create_check_constraint(
        "ck_documents_size_positive", "documents", "size_bytes > 0"
    )

    # Valid AI job status
    op.execute(
        """
        ALTER TABLE ai_jobs
        ADD CONSTRAINT ck_ai_jobs_status_valid
        CHECK (status IN ('queued', 'pending', 'processing', 'completed', 'failed'))
    """
    )

    # Valid subscription status
    op.execute(
        """
        ALTER TABLE subscriptions
        ADD CONSTRAINT ck_subscriptions_status_valid
        CHECK (status IN ('active', 'canceled', 'past_due', 'trialing'))
    """
    )

    # Valid org user role
    op.execute(
        """
        ALTER TABLE org_users
        ADD CONSTRAINT ck_org_users_role_valid
        CHECK (role IN ('owner', 'admin', 'member', 'viewer'))
    """
    )


def downgrade() -> None:
    # Drop check constraints
    op.execute(
        "ALTER TABLE org_users DROP CONSTRAINT IF EXISTS ck_org_users_role_valid"
    )
    op.execute(
        "ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS ck_subscriptions_status_valid"
    )
    op.execute("ALTER TABLE ai_jobs DROP CONSTRAINT IF EXISTS ck_ai_jobs_status_valid")
    op.drop_constraint("ck_documents_size_positive", "documents", type_="check")
    op.drop_constraint(
        "ck_organizations_max_storage_positive", "organizations", type_="check"
    )
    op.drop_constraint(
        "ck_organizations_max_users_positive", "organizations", type_="check"
    )

    # Drop unique constraints
    op.drop_constraint("uq_org_users_org_user", "org_users", type_="unique")

    # Drop indexes (only the ones we created in this migration)
    op.drop_index("ix_subscriptions_org_id", "subscriptions")
    op.drop_index("ix_audit_logs_resource", "audit_logs")
    op.drop_index("ix_audit_logs_user_id", "audit_logs")
    op.drop_index("ix_audit_logs_org_created", "audit_logs")
    op.drop_index("ix_ai_jobs_status_created", "ai_jobs")
    op.drop_index("ix_documents_owner_created", "documents")
