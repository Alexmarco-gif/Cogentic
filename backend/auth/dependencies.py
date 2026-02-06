"""
FastAPI dependencies for authentication and authorization.

Provides dependency injection for route handlers to access authenticated user context.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import utils as auth_utils
from backend.auth.exceptions import (
    InvalidTokenError,
    MissingTokenError,
    NotOrgMemberError,
)
from backend.auth.schemas import AuthContext, TokenPayload
from backend.database import get_db
from backend.repositories.user import UserRepository

logger = logging.getLogger(__name__)


async def get_token_payload(request: Request) -> TokenPayload:
    """
    Get validated token payload from request.

    If JWT middleware is enabled, reads from request.state.
    Otherwise, extracts and verifies token directly.

    Args:
        request: FastAPI request object

    Returns:
        Validated token payload

    Raises:
        AuthError: If token invalid or missing
    """
    # Check if middleware already verified token
    if hasattr(request.state, "token_payload"):
        return request.state.token_payload

    # Fallback: verify token directly (if middleware not enabled)
    token = auth_utils.extract_token_from_header(request)
    payload = await auth_utils.verify_token(token)
    return payload


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """
    Get authenticated user context (primary dependency for protected routes).

    This is the main dependency used by route handlers. It:
    1. Verifies JWT token
    2. Validates custom claims (org_id, roles, plan)
    3. Fetches user from local DB
    4. Verifies org membership
    5. Returns complete auth context

    Usage:
        @router.get("/protected")
        async def protected_route(auth: AuthContext = Depends(get_current_user)):
            # auth.user_id, auth.org_id, auth.role available here
            ...

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        AuthContext with user identity and authorization info

    Raises:
        AuthError: If authentication fails
        InvalidClaimsError: If required claims missing
        NotOrgMemberError: If user not in org
    """
    # Get validated token payload
    payload = await get_token_payload(request)

    # Validate custom claims
    auth_utils.validate_custom_claims(payload)

    # Get or create user from local DB
    user_repo = UserRepository(db)
    user = await user_repo.get_by_auth0_id(payload.sub)

    if not user:
        # User not synced yet - this shouldn't happen if webhooks working
        logger.warning(f"User {payload.sub} not found in local DB, creating...")

        # Extract email from token (if available)
        email = (
            payload.sub.split("|")[-1]
            if "|" in payload.sub
            else f"{payload.sub}@unknown.com"
        )

        user = await user_repo.create(
            auth0_id=payload.sub,
            email=email,
        )

        logger.info(f"Created user {user.id} from token")

    # Verify org membership and get role
    org_id = UUID(payload.org_id)
    user_id = UUID(str(user.id))

    # Get org membership
    from backend.repositories.organization import OrganizationRepository

    org_repo = OrganizationRepository(db)
    org_user = await org_repo.get_user_membership(org_id, user_id)

    if not org_user:
        logger.error(
            f"User {user_id} claims membership in org {org_id} but not found in org_users",
            extra={
                "user_id": str(user_id),
                "org_id": str(org_id),
                "auth0_id": payload.sub,
            },
        )
        raise NotOrgMemberError(str(org_id))

    # Build auth context
    auth_context = AuthContext(
        user_id=user_id,
        auth0_id=user.auth0_id,
        email=user.email,
        org_id=org_id,
        role=org_user.role,
        plan=payload.plan,
        is_super_admin=payload.is_super_admin,
        token_expires_at=datetime.fromtimestamp(payload.exp),
        request_id=auth_utils.get_request_id(request),
    )

    logger.debug(
        f"Auth context created: user={user.id}, org={org_id}, role={org_user.role}, super_admin={payload.is_super_admin}"
    )

    return auth_context


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthContext | None:
    """
    Get authenticated user if token provided, None otherwise.

    Use for endpoints that work with or without auth (e.g., public resources
    with optional user-specific features).

    Usage:
        @router.get("/resources")
        async def list_resources(auth: AuthContext | None = Depends(get_optional_user)):
            if auth:
                # Show user-specific resources
            else:
                # Show public resources only

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        AuthContext if authenticated, None otherwise
    """
    try:
        return await get_current_user(request, db)
    except (MissingTokenError, Exception):
        # No token or invalid token - return None (not an error for optional auth)
        return None


async def get_current_user_id(
    auth: AuthContext = Depends(get_current_user),
) -> UUID:
    """
    Convenience dependency to get just the user ID.

    Usage:
        @router.get("/me")
        async def get_profile(user_id: UUID = Depends(get_current_user_id)):
            ...
    """
    return auth.user_id


async def get_current_org_id(
    auth: AuthContext = Depends(get_current_user),
) -> UUID:
    """
    Convenience dependency to get just the org ID.

    Usage:
        @router.get("/org/settings")
        async def get_settings(org_id: UUID = Depends(get_current_org_id)):
            ...
    """
    return auth.org_id


async def get_current_user_or_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """
    Authenticate via JWT token OR API key.

    This dependency checks:
    1. First, try JWT authentication (Authorization: Bearer <token>)
    2. If no JWT, try API key authentication (X-API-Key: cogent_pk_live_...)

    API keys create a synthetic AuthContext with:
    - user_id: User who created the key
    - org_id: Organization that owns the key
    - role: "member" (API keys have limited permissions)
    - is_super_admin: False (API keys never have super admin)

    Usage:
        @router.get("/api/v1/documents")
        async def list_docs(
            auth: AuthContext = Depends(get_current_user_or_api_key)
        ):
            # Works with both JWT and API key
            ...

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        AuthContext

    Raises:
        MissingTokenError: If neither JWT nor API key provided
        InvalidTokenError: If both JWT and API key invalid
    """
    # Try JWT first
    try:
        return await get_current_user(request, db)
    except MissingTokenError:
        # No JWT, try API key
        pass

    # Check for API key in header
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        raise MissingTokenError()

    # Validate API key format
    if not api_key.startswith("cogent_pk_live_"):
        logger.warning("Invalid API key format", extra={"key_prefix": api_key[:16]})
        raise InvalidTokenError("Invalid API key format")

    # Look up API key
    from backend.repositories.api_key import APIKeyRepository

    api_key_repo = APIKeyRepository(db)
    api_key_model = await api_key_repo.get_by_key(api_key)

    if not api_key_model or not api_key_model.is_active:
        logger.warning(
            "API key not found or inactive",
            extra={
                "key_prefix": api_key[:16],
                "found": api_key_model is not None,
                "active": api_key_model.is_active if api_key_model else False,
            },
        )
        raise InvalidTokenError("Invalid or revoked API key")

    # Get user who created the key
    from backend.repositories.user import UserRepository

    user_repo = UserRepository(db)
    user = await user_repo.get(api_key_model.created_by_user_id)

    if not user:
        logger.error(
            f"API key creator user {api_key_model.created_by_user_id} not found"
        )
        raise InvalidTokenError("API key user not found")

    # Get org membership to determine role
    from backend.repositories.organization import OrganizationRepository

    org_repo = OrganizationRepository(db)
    org_user = await org_repo.get_user_membership(api_key_model.org_id, user.id)

    if not org_user:
        logger.error(f"API key user {user.id} not member of org {api_key_model.org_id}")
        raise InvalidTokenError("API key user not org member")

    # Build auth context for API key
    # API keys inherit the role of the user who created them
    auth_context = AuthContext(
        user_id=user.id,
        auth0_id=user.auth0_id,
        email=user.email,
        org_id=api_key_model.org_id,
        role=org_user.role,
        plan="free",  # API keys don't have plan context
        is_super_admin=False,  # API keys never have super admin
        token_expires_at=api_key_model.expires_at or datetime(2099, 1, 1),
        request_id=auth_utils.get_request_id(request),
    )

    logger.info(
        f"API key authentication: key={api_key_model.key_prefix}..., user={user.id}, org={api_key_model.org_id}",
        extra={
            "api_key_id": str(api_key_model.id),
            "api_key_name": api_key_model.name,
            "user_id": str(user.id),
            "org_id": str(api_key_model.org_id),
        },
    )

    return auth_context


def get_feature_flags_service():
    """
    Dependency to inject FeatureFlagService into route handlers.

    Usage:
        from backend.services.feature_flags import FeatureFlagService

        @router.get("/features")
        async def list_features(
            auth: AuthContext = Depends(get_current_user),
            flags: FeatureFlagService = Depends(get_feature_flags_service)
        ):
            enabled = flags.get_enabled_features(
                user_id=str(auth.user_id),
                org_id=str(auth.org_id),
                plan=auth.plan
            )
            return {"enabled_features": enabled}

    Returns:
        FeatureFlagService singleton instance
    """
    from backend.services.feature_flags import get_feature_flags_service as get_service

    return get_service()
