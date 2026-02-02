"""Mako template for migration scripts"""

"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '600f4a29ec2b'
down_revision: Union[str, None] = 'a762f3897625'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === INDEXES FOR PERFORMANCE ===
    
    # Users table - login and Auth0 lookups
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_auth0_id', 'users', ['auth0_id'], unique=True)
    
    # Documents table - "my documents" queries
    op.create_index('ix_documents_owner_created', 'documents', ['owner_id', 'created_at'])
    op.create_index('ix_documents_org_id', 'documents', ['org_id'])
    
    # AI Jobs table - queue processing
    op.create_index('ix_ai_jobs_status_created', 'ai_jobs', ['status', 'created_at'])
    op.create_index('ix_ai_jobs_org_id', 'ai_jobs', ['org_id'])
    
    # Audit logs table - audit trail queries
    op.create_index('ix_audit_logs_org_created', 'audit_logs', ['org_id', 'created_at'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
    
    # Org Users table - membership lookups
    op.create_index('ix_org_users_org_id', 'org_users', ['org_id'])
    op.create_index('ix_org_users_user_id', 'org_users', ['user_id'])
    
    # Subscriptions table - org lookup
    op.create_index('ix_subscriptions_org_id', 'subscriptions', ['org_id'], unique=True)
    
    # === UNIQUE CONSTRAINTS ===
    
    # Prevent duplicate org memberships
    op.create_unique_constraint('uq_org_users_org_user', 'org_users', ['org_id', 'user_id'])
    
    # === CHECK CONSTRAINTS ===
    
    # Ensure positive limits
    op.create_check_constraint('ck_organizations_max_users_positive', 'organizations', 'max_users > 0')
    op.create_check_constraint('ck_organizations_max_storage_positive', 'organizations', 'max_storage_gb > 0')
    
    # Valid document sizes
    op.create_check_constraint('ck_documents_size_positive', 'documents', 'size_bytes > 0')
    
    # Valid AI job status
    op.execute("""
        ALTER TABLE ai_jobs 
        ADD CONSTRAINT ck_ai_jobs_status_valid 
        CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
    """)
    
    # Valid subscription status
    op.execute("""
        ALTER TABLE subscriptions 
        ADD CONSTRAINT ck_subscriptions_status_valid 
        CHECK (status IN ('active', 'canceled', 'past_due', 'trialing'))
    """)
    
    # Valid org user role
    op.execute("""
        ALTER TABLE org_users 
        ADD CONSTRAINT ck_org_users_role_valid 
        CHECK (role IN ('owner', 'admin', 'member', 'viewer'))
    """)


def downgrade() -> None:
    # Drop check constraints
    op.execute("ALTER TABLE org_users DROP CONSTRAINT IF EXISTS ck_org_users_role_valid")
    op.execute("ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS ck_subscriptions_status_valid")
    op.execute("ALTER TABLE ai_jobs DROP CONSTRAINT IF EXISTS ck_ai_jobs_status_valid")
    op.drop_constraint('ck_documents_size_positive', 'documents', type_='check')
    op.drop_constraint('ck_organizations_max_storage_positive', 'organizations', type_='check')
    op.drop_constraint('ck_organizations_max_users_positive', 'organizations', type_='check')
    
    # Drop unique constraints
    op.drop_constraint('uq_org_users_org_user', 'org_users', type_='unique')
    
    # Drop indexes
    op.drop_index('ix_subscriptions_org_id', 'subscriptions')
    op.drop_index('ix_org_users_user_id', 'org_users')
    op.drop_index('ix_org_users_org_id', 'org_users')
    op.drop_index('ix_audit_logs_resource', 'audit_logs')
    op.drop_index('ix_audit_logs_user_id', 'audit_logs')
    op.drop_index('ix_audit_logs_org_created', 'audit_logs')
    op.drop_index('ix_ai_jobs_org_id', 'ai_jobs')
    op.drop_index('ix_ai_jobs_status_created', 'ai_jobs')
    op.drop_index('ix_documents_org_id', 'documents')
    op.drop_index('ix_documents_owner_created', 'documents')
    op.drop_index('ix_users_auth0_id', 'users')
    op.drop_index('ix_users_email', 'users')
