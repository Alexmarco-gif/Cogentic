"""
Authorization guards for RBAC and resource ownership.

These functions enforce authorization rules throughout the application.
They raise ForbiddenError when access is denied.
"""

import logging
from typing import Any
from uuid import UUID

from prometheus_client import Counter

from backend.auth.enums import Role, role_hierarchy_check
from backend.auth.exceptions import (
    FeatureDisabledError,
    ForbiddenError,
    InsufficientRoleError,
    NotOrgMemberError,
    NotResourceOwnerError,
)
from backend.auth.schemas import AuthContext

logger = logging.getLogger(__name__)

# Prometheus counter for admin override events — feeds alerting dashboards.
admin_override_total = Counter(
    "cogent_admin_override_total",
    "Super admin bypass events",
    ["admin_user_id", "action"],
)


def require_role(auth: AuthContext, min_role: str | Role) -> None:
    """
    Require user to have minimum role level.

    Enforces role hierarchy: Owner > Admin > Member > Viewer

    Args:
        auth: Authenticated user context
        min_role: Minimum required role (string or enum)

    Raises:
        InsufficientRoleError: If user role insufficient

    Examples:
        # Require Admin or Owner
        require_role(auth, Role.ADMIN)
        require_role(auth, "admin")

        # Require Member or higher
        require_role(auth, Role.MEMBER)
    """
    if not role_hierarchy_check(auth.role, min_role):
        # Convert to Role enum for logging
        min_role_enum = (
            Role.from_string(min_role) if isinstance(min_role, str) else min_role
        )

        logger.warning(
            f"Role check failed: user has {auth.role}, needs {min_role_enum.to_string()}",
            extra={
                "user_id": str(auth.user_id),
                "org_id": str(auth.org_id),
                "current_role": auth.role,
                "required_role": min_role_enum.to_string(),
                "request_id": auth.request_id,
            },
        )

        raise InsufficientRoleError(
            required_role=min_role_enum.to_string(), current_role=auth.role
        )


def require_org_membership(auth: AuthContext, org_id: UUID) -> None:
    """
    Require user to be a member of the specified organization.

    Super admins can bypass this check (with audit logging).

    Args:
        auth: Authenticated user context
        org_id: Organization ID to check

    Raises:
        NotOrgMemberError: If user not a member of the org

    Example:
        require_org_membership(auth, org_id)
    """
    # Super admin override
    if auth.is_super_admin and auth.org_id != org_id:
        logger.warning(
            "SUPER ADMIN OVERRIDE: Bypassing org membership check",
            extra={
                "admin_user_id": str(auth.user_id),
                "admin_org_id": str(auth.org_id),
                "target_org_id": str(org_id),
                "request_id": auth.request_id,
                "security_event": "admin_override",
            },
        )

        # Prometheus metric for dashboard alerting
        admin_override_total.labels(
            admin_user_id=str(auth.user_id), action="org_membership_bypass"
        ).inc()

        # Real-time Sentry alert (non-fatal, but security-notable)
        _sentry_capture_admin_override(
            admin_user_id=auth.user_id,
            target_org_id=org_id,
            action="org_membership_bypass",
            request_id=auth.request_id,
        )

        return

    if auth.org_id != org_id:
        logger.warning(
            f"Org membership check failed: user in {auth.org_id}, accessing {org_id}",
            extra={
                "user_id": str(auth.user_id),
                "user_org_id": str(auth.org_id),
                "requested_org_id": str(org_id),
                "request_id": auth.request_id,
            },
        )

        raise NotOrgMemberError(str(org_id))


def require_resource_ownership(
    auth: AuthContext,
    resource: Any,
    resource_type: str,
    allow_admin: bool = True,
) -> None:
    """
    Require user to own the resource (or be admin if allow_admin=True).

    Args:
        auth: Authenticated user context
        resource: Resource object (must have owner_id or created_by attribute)
        resource_type: Resource type name (for error messages)
        allow_admin: If True, Admins and Owners can access any resource

    Raises:
        NotResourceOwnerError: If user doesn't own resource and isn't admin
        AttributeError: If resource doesn't have owner_id/created_by

    Examples:
        # Only owner can edit
        require_resource_ownership(auth, document, "document", allow_admin=False)

        # Owner or Admin+ can edit
        require_resource_ownership(auth, document, "document", allow_admin=True)
    """
    # Get resource owner ID
    owner_id = None
    if hasattr(resource, "owner_id"):
        owner_id = resource.owner_id
    elif hasattr(resource, "created_by"):
        owner_id = resource.created_by
    else:
        raise AttributeError(
            f"Resource {resource_type} must have 'owner_id' or 'created_by' attribute"
        )

    # Check ownership
    is_owner = owner_id == auth.user_id
    is_admin = role_hierarchy_check(auth.role, Role.ADMIN)

    if is_owner:
        # User owns the resource
        return

    if allow_admin and is_admin:
        # Admin/Owner can access any resource in their org
        logger.info(
            f"Admin override: {auth.role} accessing {resource_type}",
            extra={
                "user_id": str(auth.user_id),
                "org_id": str(auth.org_id),
                "resource_type": resource_type,
                "resource_owner": str(owner_id),
                "request_id": auth.request_id,
            },
        )
        return

    # Access denied
    logger.warning(
        f"Ownership check failed: user {auth.user_id} accessing {resource_type} owned by {owner_id}",
        extra={
            "user_id": str(auth.user_id),
            "org_id": str(auth.org_id),
            "resource_type": resource_type,
            "resource_owner": str(owner_id),
            "user_role": auth.role,
            "request_id": auth.request_id,
        },
    )

    raise NotResourceOwnerError(
        resource_type=resource_type, resource_id=str(getattr(resource, "id", "unknown"))
    )


def require_owner(auth: AuthContext) -> None:
    """
    Require user to be an Owner (highest privilege).

    Shorthand for require_role(auth, Role.OWNER)

    Args:
        auth: Authenticated user context

    Raises:
        InsufficientRoleError: If user is not an owner
    """
    require_role(auth, Role.OWNER)


def require_admin(auth: AuthContext) -> None:
    """
    Require user to be Admin or Owner.

    Shorthand for require_role(auth, Role.ADMIN)

    Args:
        auth: Authenticated user context

    Raises:
        InsufficientRoleError: If user is not admin or higher
    """
    require_role(auth, Role.ADMIN)


def require_member(auth: AuthContext) -> None:
    """
    Require user to be Member or higher.

    Shorthand for require_role(auth, Role.MEMBER)

    Args:
        auth: Authenticated user context

    Raises:
        InsufficientRoleError: If user is viewer
    """
    require_role(auth, Role.MEMBER)


def can_manage_member(auth: AuthContext, target_role: str) -> bool:
    """
    Check if user can manage a member with target_role.

    Rules:
    - Admins can manage Members and Viewers (not Owners or other Admins)
    - Owners can manage everyone

    Args:
        auth: Authenticated user context
        target_role: Role of the member to manage

    Returns:
        True if user can manage this member

    Examples:
        # Can admin change a member's role?
        if can_manage_member(auth, "member"):
            # Yes, proceed
            ...
    """
    user_role = Role.from_string(auth.role)
    target = Role.from_string(target_role)

    if user_role == Role.OWNER:
        # Owners can manage everyone
        return True

    if user_role == Role.ADMIN:
        # Admins can manage Members and Viewers (not Owners or other Admins)
        return target < Role.ADMIN

    # Members and Viewers cannot manage anyone
    return False


def require_can_manage_member(auth: AuthContext, target_role: str) -> None:
    """
    Require user to have permission to manage member with target_role.

    Args:
        auth: Authenticated user context
        target_role: Role of the member to manage

    Raises:
        ForbiddenError: If user cannot manage this member

    Example:
        require_can_manage_member(auth, existing_member.role)
    """
    if not can_manage_member(auth, target_role):
        logger.warning(
            f"Cannot manage member: {auth.role} trying to manage {target_role}",
            extra={
                "user_id": str(auth.user_id),
                "user_role": auth.role,
                "target_role": target_role,
                "request_id": auth.request_id,
            },
        )

        raise ForbiddenError(
            message="Insufficient permissions to manage this member",
            details={
                "user_role": auth.role,
                "target_role": target_role,
            },
        )


def require_feature(
    auth: AuthContext,
    feature_name: str,
) -> None:
    """
    Deprecated synchronous feature guard.

    Runtime feature enforcement is handled by
    ``backend.middleware.feature_gating.require_feature`` so all access checks use
    the database-backed feature gate configuration. This helper is retained only
    to fail loudly if stale code paths still try to use the old synchronous
    auth-context-only contract.

    Args:
        auth: Authenticated user context
        feature_name: Name of the feature to check

    Raises:
        FeatureDisabledError: If feature is not available

    Example:
        # Deprecated. Use backend.middleware.feature_gating.require_feature instead.
        require_feature(auth, "ai_document_summarization")
    """
    logger.error(
        "Deprecated auth.guards.require_feature invoked for %s",
        feature_name,
        extra={
            "feature": feature_name,
            "user_id": str(auth.user_id),
            "org_id": str(auth.org_id),
            "request_id": auth.request_id,
        },
    )
    raise FeatureDisabledError(
        feature_name=feature_name,
        reason=(
            "Feature checks must use backend.middleware.feature_gating.require_feature "
            "so route access is enforced from the database-backed gate registry."
        ),
    )


# ── Security Alerting Helpers ─────────────────────────────────────────────────


def _sentry_capture_admin_override(
    *,
    admin_user_id: UUID,
    target_org_id: UUID,
    action: str,
    request_id: str | None,
) -> None:
    """Send a Sentry event for a super admin override.

    Non-blocking — if Sentry SDK is not installed or not initialised
    the call is silently discarded.
    """
    try:
        import sentry_sdk

        sentry_sdk.capture_message(
            f"SUPER ADMIN OVERRIDE: {action}",
            level="warning",
            extras={
                "admin_user_id": str(admin_user_id),
                "target_org_id": str(target_org_id),
                "action": action,
                "request_id": request_id,
            },
            tags={
                "security_event": "admin_override",
                "action": action,
            },
        )
    except Exception:
        # Alerting must never break the request path
        pass
