"""
Auth introspection endpoints.

Provides information about the authenticated user and their permissions.
"""

from typing import Any

from fastapi import APIRouter, Depends

from backend.auth import AuthContext, get_current_user, get_user_permissions

router = APIRouter(prefix="/auth")


@router.get("/me")
async def get_current_user_info(
    auth: AuthContext = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get current authenticated user information.

    Returns user context including:
    - User ID and email
    - Organization context
    - Role and permissions
    - Token expiration
    - Subscription plan

    This endpoint is useful for:
    - Frontend to check authentication status
    - Getting user's current organization context
    - Determining UI permissions
    """
    permissions = get_user_permissions(auth)

    return {
        "user": {
            "id": str(auth.user_id),
            "auth0_id": auth.auth0_id,
            "email": auth.email,
        },
        "organization": {
            "id": str(auth.org_id),
            "role": auth.role,
        },
        "subscription": {
            "plan": auth.plan,
        },
        "permissions": permissions,
        "token": {
            "expires_at": auth.token_expires_at.isoformat(),
        },
    }


@router.get("/permissions")
async def get_permissions(
    auth: AuthContext = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get detailed permission matrix for current user.

    Useful for:
    - Frontend feature flags
    - Conditional UI rendering
    - Permission debugging
    """
    permissions = get_user_permissions(auth)

    return {
        "user_id": str(auth.user_id),
        "org_id": str(auth.org_id),
        "role": auth.role,
        "permissions": permissions,
    }


@router.get("/token/verify")
async def verify_token(
    auth: AuthContext = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Verify token is valid and return basic info.

    Lightweight endpoint for token validation without full user context.
    """
    return {
        "valid": True,
        "user_id": str(auth.user_id),
        "org_id": str(auth.org_id),
        "expires_at": auth.token_expires_at.isoformat(),
    }
