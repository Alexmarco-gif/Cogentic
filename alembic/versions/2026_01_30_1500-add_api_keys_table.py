"""Add API keys table for M2M authentication

Revision ID: 2026_01_30_1500
Revises: 600f4a29ec2b
Create Date: 2026-01-30 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '2026_01_30_1500'
down_revision = '600f4a29ec2b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('key_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('key_prefix', sa.String(16), nullable=False),
        sa.Column('org_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('scopes', sa.Text, nullable=False, server_default='read:documents,write:documents'),
        sa.Column('rate_limit', sa.Integer, nullable=False, server_default='100'),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('revoked_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime, nullable=True),
    )
    
    # Create indexes
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'])
    op.create_index('ix_api_keys_key_prefix', 'api_keys', ['key_prefix'])
    op.create_index('ix_api_keys_org_id', 'api_keys', ['org_id'])
    
    # Create compound index for active key lookup
    op.create_index(
        'ix_api_keys_active_lookup',
        'api_keys',
        ['org_id', 'revoked_at', 'expires_at'],
        postgresql_where=sa.text('deleted_at IS NULL')
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_api_keys_active_lookup', table_name='api_keys')
    op.drop_index('ix_api_keys_org_id', table_name='api_keys')
    op.drop_index('ix_api_keys_key_prefix', table_name='api_keys')
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    
    # Drop table
    op.drop_table('api_keys')
