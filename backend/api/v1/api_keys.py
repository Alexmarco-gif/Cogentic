"""
API Key management endpoints

Allows organizations to create, list, and revoke API keys for M2M authentication.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.guards import require_org_membership, require_role
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.repositories.api_key import APIKeyRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


# Request/Response Models


class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key"""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Human-readable name"
    )
    description: str | None = Field(None, description="Optional description")
    scopes: list[str] = Field(
        default_factory=lambda: ["read:documents", "write:documents"],
        description="Permission scopes",
    )
    rate_limit: int = Field(100, ge=10, le=10000, description="Requests per minute")
    expires_in_days: int | None = Field(
        None, ge=1, le=365, description="Days until expiration (optional)"
    )


class APIKeyResponse(BaseModel):
    """API key metadata (without the actual key)"""

    id: UUID
    name: str
    description: str | None
    key_prefix: str
    scopes: list[str]
    rate_limit: int
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    is_active: bool


class CreateAPIKeyResponse(BaseModel):
    """Response when creating a new API key (includes the actual key)"""

    api_key: str = Field(..., description="The actual API key - ONLY SHOWN ONCE")
    key_id: UUID
    key_prefix: str
    expires_at: datetime | None

    class Config:
        json_schema_extra = {
            "example": {
                "api_key": "cogent_pk_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
                "key_id": "123e4567-e89b-12d3-a456-426614174000",
                "key_prefix": "cogent_pk_live_a1",
                "expires_at": "2027-01-30T10:00:00Z",
            }
        }


# Endpoints


@router.post(
    "/orgs/{org_id}/api-keys",
    response_model=CreateAPIKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    org_id: UUID,
    request: CreateAPIKeyRequest,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new API key for the organization.

    **Permissions:** Admin or Owner

    **WARNING:** The actual API key is only returned once! Save it securely.

    Returns:
        The API key metadata and the actual key (only shown once)
    """
    # Verify org membership and admin+ role
    require_org_membership(auth, org_id)
    require_role(auth, "admin")

    # Check max API keys limit (prevent abuse)
    repo = APIKeyRepository(db)
    active_count = await repo.count_active_by_org(org_id)

    MAX_API_KEYS_PER_ORG = 50
    if active_count >= MAX_API_KEYS_PER_ORG:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum {MAX_API_KEYS_PER_ORG} active API keys per organization",
        )

    # Create API key
    api_key_model, plaintext_key = await repo.create_key(
        org_id=org_id,
        created_by_user_id=auth.user_id,
        name=request.name,
        description=request.description,
        scopes=request.scopes,
        rate_limit=request.rate_limit,
        expires_in_days=request.expires_in_days,
    )

    await db.commit()

    logger.info(
        f"API key created: {api_key_model.key_prefix}... by user {auth.user_id}",
        extra={
            "api_key_id": str(api_key_model.id),
            "api_key_name": api_key_model.name,
            "org_id": str(org_id),
            "created_by": str(auth.user_id),
        },
    )

    return CreateAPIKeyResponse(
        api_key=plaintext_key,
        key_id=api_key_model.id,
        key_prefix=api_key_model.key_prefix,
        expires_at=api_key_model.expires_at,
    )


@router.get("/orgs/{org_id}/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    org_id: UUID,
    include_revoked: bool = False,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all API keys for the organization.

    **Permissions:** Admin or Owner

    Args:
        org_id: Organization ID
        include_revoked: Include revoked keys in results

    Returns:
        List of API key metadata (without actual keys)
    """
    # Verify org membership and admin+ role
    require_org_membership(auth, org_id)
    require_role(auth, "admin")

    repo = APIKeyRepository(db)
    api_keys = await repo.list_by_org(org_id, include_revoked=include_revoked)

    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            description=key.description,
            key_prefix=key.key_prefix,
            scopes=key.scopes_list,
            rate_limit=key.rate_limit,
            created_at=key.created_at,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at,
            revoked_at=key.revoked_at,
            is_active=key.is_active,
        )
        for key in api_keys
    ]


@router.delete(
    "/orgs/{org_id}/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def revoke_api_key(
    org_id: UUID,
    key_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke an API key (makes it inactive).

    **Permissions:** Admin or Owner

    **Note:** Revoked keys cannot be reactivated. Create a new key instead.

    Args:
        org_id: Organization ID
        key_id: API key ID to revoke
    """
    # Verify org membership and admin+ role
    require_org_membership(auth, org_id)
    require_role(auth, "admin")

    repo = APIKeyRepository(db)
    api_key = await repo.get(key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    # Verify key belongs to org
    if api_key.org_id != org_id:
        logger.warning(
            "Attempted to revoke API key from different org",
            extra={
                "user_id": str(auth.user_id),
                "user_org": str(org_id),
                "key_org": str(api_key.org_id),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    # Revoke key
    await repo.revoke(key_id)
    await db.commit()

    logger.info(
        f"API key revoked: {api_key.key_prefix}... by user {auth.user_id}",
        extra={
            "api_key_id": str(key_id),
            "api_key_name": api_key.name,
            "org_id": str(org_id),
            "revoked_by": str(auth.user_id),
        },
    )

    return None


@router.get("/orgs/{org_id}/api-keys/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    org_id: UUID,
    key_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get details for a specific API key.

    **Permissions:** Admin or Owner

    **Note:** The actual API key is never returned (only the prefix).

    Args:
        org_id: Organization ID
        key_id: API key ID

    Returns:
        API key metadata
    """
    # Verify org membership and admin+ role
    require_org_membership(auth, org_id)
    require_role(auth, "admin")

    repo = APIKeyRepository(db)
    api_key = await repo.get(key_id)

    if not api_key or api_key.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        description=api_key.description,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes_list,
        rate_limit=api_key.rate_limit,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
        is_active=api_key.is_active,
    )
