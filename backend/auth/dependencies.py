"""
FastAPI dependencies for authentication and authorization.

Provides dependency injection for route handlers to access authenticated user context.
"""

import logging
from datetime import datetime
from typing import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
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


def require_permissions(permissions: list[str]) -> Callable:
    """
    Dependency factory that checks if user has required permissions.

    Args:
        permissions: List of permission strings required (e.g., ["view_signals", "admin"])

    Returns:
        FastAPI dependency that validates permissions and returns AuthContext

    Usage:
        @router.get("/admin")
        async def admin_endpoint(
            auth: AuthContext = Depends(require_permissions(["admin"]))
        ):
            ...
    """

    async def permission_checker(
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> AuthContext:
        auth = await get_current_user(request, db)

        # Super admins bypass all permission checks
        if auth.is_super_admin:
            return auth

        # Map user role to a hierarchy level
        user_role = auth.role.lower() if auth.role else "viewer"

        role_hierarchy = {
            "owner": ["owner", "admin", "analyst", "member", "viewer"],
            "admin": ["admin", "analyst", "member", "viewer"],
            "analyst": ["analyst", "member", "viewer"],
            "member": ["member", "viewer"],
            "viewer": ["viewer"],
        }

        allowed_roles = role_hierarchy.get(user_role, ["viewer"])

        # Check if any required permission/role is satisfied
        for permission in permissions:
            if permission.lower() in allowed_roles:
                return auth

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {permissions}",
        )

    return permission_checker


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
    3. For M2M tokens: Uses claims directly from token
    4. For user tokens: Fetches user from local DB and verifies org membership
    5. Returns complete auth context

    Supports both regular user tokens and M2M (client-credentials) tokens.
    M2M tokens must have custom claims set via Auth0 Client Credentials Exchange Action.

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

    # Handle M2M (client-credentials) tokens differently
    if payload.is_m2m_token:
        return await _handle_m2m_token(payload, request)

    # Regular user token flow
    return await _handle_user_token(payload, request, db)


async def _handle_m2m_token(payload: TokenPayload, request: Request) -> AuthContext:
    """
    Handle M2M (client-credentials) token authentication.

    M2M tokens contain all required claims set by Auth0 Client Credentials Exchange Action:
    - org_id: Organization the service acts on behalf of
    - user_id: Service user ID
    - role: Role for authorization
    - email: Service account email (optional)

    Args:
        payload: Validated M2M token payload
        request: FastAPI request

    Returns:
        AuthContext built from M2M token claims
    """
    org_id = UUID(payload.org_id)
    user_id = UUID(payload.user_id)
    role = payload.role or "member"
    email = payload.email or f"m2m-{payload.sub}@service.cogent.ai"

    auth_context = AuthContext(
        user_id=user_id,
        auth0_id=payload.sub,  # For M2M, this is the client ID
        email=email,
        org_id=org_id,
        role=role,
        plan=payload.plan,
        is_super_admin=payload.is_super_admin,
        token_expires_at=datetime.fromtimestamp(payload.exp),
        request_id=auth_utils.get_request_id(request),
    )

    logger.info(
        f"M2M auth context created: client={payload.sub}, org={org_id}, role={role}",
        extra={
            "client_id": payload.sub,
            "org_id": str(org_id),
            "user_id": str(user_id),
            "role": role,
            "grant_type": "client-credentials",
        },
    )

    return auth_context


async def _handle_user_token(
    payload: TokenPayload, request: Request, db: AsyncSession
) -> AuthContext:
    """
    Handle regular user token authentication.

    Args:
        payload: Validated user token payload
        request: FastAPI request
        db: Database session

    Returns:
        AuthContext with user identity from local DB
    """
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
