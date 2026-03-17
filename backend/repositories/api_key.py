"""
API Key repository for M2M authentication
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.api_key import APIKey
from backend.repositories.base import BaseRepository


class APIKeyRepository(BaseRepository[APIKey]):
    """Repository for API key CRUD operations"""

    def __init__(self, db: AsyncSession):
        super().__init__(APIKey, db)

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """
        Generate a new API key.

        Returns:
            tuple: (full_key, key_hash, key_prefix)
                - full_key: The actual API key to return to user (only shown once)
                - key_hash: SHA256 hash to store in database
                - key_prefix: First 12 chars for identification
        """
        # Generate 32 random bytes (256 bits)
        random_part = secrets.token_urlsafe(32)

        # Format: cogent_pk_live_{random}
        full_key = f"cogent_pk_live_{random_part}"

        # Hash for storage (never store plain key)
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()

        # Prefix for display (first 16 chars including prefix)
        key_prefix = full_key[:16]

        return full_key, key_hash, key_prefix

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key for lookup"""
        return hashlib.sha256(key.encode()).hexdigest()

    async def create_key(
        self,
        org_id: UUID,
        created_by_user_id: UUID,
        name: str,
        description: str | None = None,
        scopes: list[str] | None = None,
        rate_limit: int = 100,
        expires_in_days: int | None = None,
    ) -> tuple[APIKey, str]:
        """
        Create a new API key.

        Args:
            org_id: Organization ID
            created_by_user_id: User who created the key
            name: Human-readable name
            description: Optional description
            scopes: List of permission scopes (default: read:documents,write:documents)
            rate_limit: Requests per minute (default: 100)
            expires_in_days: Days until expiration (None = never expires)

        Returns:
            tuple: (APIKey model, plaintext_key)
                WARNING: plaintext_key is only returned once, must be shown to user
        """
        # Generate key
        full_key, key_hash, key_prefix = self.generate_key()

        # Default scopes
        if scopes is None:
            scopes = ["read:documents", "write:documents"]

        scopes_str = ",".join(scopes)

        # Calculate expiration
        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        # Create key record
        api_key = await self.create(
            key_hash=key_hash,
            key_prefix=key_prefix,
            org_id=org_id,
            created_by_user_id=created_by_user_id,
            name=name,
            description=description,
            scopes=scopes_str,
            rate_limit=rate_limit,
            expires_at=expires_at,
        )

        return api_key, full_key

    async def get_by_key(self, key: str) -> APIKey | None:
        """
        Find API key by plaintext key (hashes and looks up).

        Args:
            key: Plaintext API key (cogent_pk_live_...)

        Returns:
            APIKey model if found and active, None otherwise
        """
        key_hash = self.hash_key(key)

        result = await self.db.execute(
            select(APIKey)
            .where(APIKey.key_hash == key_hash)
            .where(APIKey.deleted_at.is_(None))
        )

        api_key = result.scalar_one_or_none()

        # Update last_used_at if found and active
        if api_key and api_key.is_active:
            api_key.last_used_at = datetime.now(timezone.utc)
            await self.db.flush()

        return api_key

    async def list_by_org(
        self,
        org_id: UUID,
        include_revoked: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[APIKey]:
        """
        List all API keys for an organization (paginated).

        Args:
            org_id: Organization ID
            include_revoked: Include revoked keys in results
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of APIKey models
        """
        query = (
            select(APIKey)
            .where(APIKey.org_id == org_id)
            .where(APIKey.deleted_at.is_(None))
            .order_by(APIKey.created_at.desc())
        )

        if not include_revoked:
            query = query.where(APIKey.revoked_at.is_(None))

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def revoke(self, api_key_id: UUID) -> APIKey | None:
        """
        Revoke an API key (soft delete alternative - key still exists but inactive).

        Args:
            api_key_id: API key UUID

        Returns:
            Updated APIKey model or None if not found
        """
        api_key = await self.get(api_key_id)

        if api_key:
            api_key.revoked_at = datetime.now(timezone.utc)
            await self.db.flush()

        return api_key

    async def count_active_by_org(self, org_id: UUID) -> int:
        """Count active API keys for an organization"""
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count(APIKey.id))
            .where(APIKey.org_id == org_id)
            .where(APIKey.deleted_at.is_(None))
            .where(APIKey.revoked_at.is_(None))
        )

        return result.scalar() or 0

    async def rotate_key(
        self,
        old_key_id: UUID,
        rotated_by_user_id: UUID,
        grace_period_hours: int = 24,
    ) -> tuple[APIKey, str]:
        """Rotate an API key: create a replacement and schedule old-key revocation.

        The old key remains active for ``grace_period_hours`` so that
        consumers have time to switch over.

        Args:
            old_key_id: ID of the existing key to rotate.
            rotated_by_user_id: User performing the rotation.
            grace_period_hours: Hours the old key stays valid (default 24).

        Returns:
            (new_APIKey, plaintext_new_key) — caller must show the plaintext once.

        Raises:
            ValueError: If the old key is not found or already revoked.
        """
        old_key = await self.get(old_key_id)
        if old_key is None or old_key.revoked_at is not None:
            raise ValueError("API key not found or already revoked")

        # Create the replacement with the same config
        new_key_model, plaintext_key = await self.create_key(
            org_id=old_key.org_id,
            created_by_user_id=rotated_by_user_id,
            name=f"{old_key.name} (rotated)",
            description=old_key.description,
            scopes=old_key.scopes_list,
            rate_limit=old_key.rate_limit,
            expires_in_days=(
                int((old_key.expires_at - datetime.now(timezone.utc)).days)
                if old_key.expires_at
                else None
            ),
        )

        # Schedule the old key for deferred revocation
        old_key.expires_at = datetime.now(timezone.utc) + timedelta(
            hours=grace_period_hours
        )
        await self.db.flush()

        return new_key_model, plaintext_key
