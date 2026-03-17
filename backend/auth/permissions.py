"""
Permission checking utilities for fine-grained authorization.

These functions provide boolean permission checks without raising exceptions.
Use for conditional logic where you need to check permissions without enforcement.
"""

import logging
from typing import Any
from uuid import UUID

from backend.auth.enums import Role, get_role_capabilities
from backend.auth.schemas import AuthContext

logger = logging.getLogger(__name__)


def can_view_resource(auth: AuthContext, resource: Any) -> bool:
    """
    Check if user can view a resource.

    Rules:
    - All roles can view resources in their org
    - Private resources: only owner + admins
    - Shared resources: owner + shared_with users + admins
    - Org/public resources: all org members

    Args:
        auth: Authenticated user context
        resource: Resource object (must have visibility, owner_id, shared_with)

    Returns:
        True if user can view resource
    """
    # Admin/Owner can view everything in their org
    if Role.from_string(auth.role) >= Role.ADMIN:
        return True

    # Check visibility
    visibility = getattr(resource, "visibility", "private")
    owner_id = getattr(resource, "owner_id", None)

    if visibility == "private":
        # Only owner + admins
        return owner_id == auth.user_id

    if visibility == "shared":
        # Owner + shared_with + admins
        if owner_id == auth.user_id:
            return True
        shared_with = getattr(resource, "shared_with", [])
        return str(auth.user_id) in shared_with

    # Org/public visibility - all org members can view
    return True


def can_edit_resource(auth: AuthContext, resource: Any) -> bool:
    """
    Check if user can edit a resource.

    Rules:
    - Owner can always edit own resources
    - Admin/Owner can edit any resource in org
    - Members cannot edit others' resources
    - Viewers cannot edit anything

    Args:
        auth: Authenticated user context
        resource: Resource object (must have owner_id)

    Returns:
        True if user can edit resource
    """
    user_role = Role.from_string(auth.role)
    caps = get_role_capabilities(user_role)

    # Can this role edit anything?
    if not caps["can_edit_own"]:
        return False

    owner_id = getattr(resource, "owner_id", None)
    is_owner = owner_id == auth.user_id

    # Owner can edit own resource
    if is_owner and caps["can_edit_own"]:
        return True

    # Admin+ can edit any resource
    return bool(caps["can_edit_all"])


def can_delete_resource(auth: AuthContext, resource: Any) -> bool:
    """
    Check if user can delete a resource.

    Rules:
    - Owner can delete own resources
    - Admin/Owner can delete any resource in org
    - Members cannot delete others' resources
    - Viewers cannot delete anything

    Args:
        auth: Authenticated user context
        resource: Resource object (must have owner_id)

    Returns:
        True if user can delete resource
    """
    user_role = Role.from_string(auth.role)
    caps = get_role_capabilities(user_role)

    # Can this role delete anything?
    if not caps["can_delete_own"]:
        return False

    owner_id = getattr(resource, "owner_id", None)
    is_owner = owner_id == auth.user_id

    # Owner can delete own resource
    if is_owner and caps["can_delete_own"]:
        return True

    # Admin+ can delete any resource
    return bool(caps["can_delete_all"])


def can_create_resource(auth: AuthContext) -> bool:
    """
    Check if user can create resources.

    Rules:
    - Viewers: No
    - Members+: Yes

    Args:
        auth: Authenticated user context

    Returns:
        True if user can create resources
    """
    user_role = Role.from_string(auth.role)
    caps = get_role_capabilities(user_role)
    return caps["can_create"]


def can_manage_members(auth: AuthContext) -> bool:
    """
    Check if user can manage org members.

    Rules:
    - Admin+: Yes (but admins cannot manage owners/other admins)
    - Member/Viewer: No

    Args:
        auth: Authenticated user context

    Returns:
        True if user can manage members
    """
    user_role = Role.from_string(auth.role)
    caps = get_role_capabilities(user_role)
    return caps["can_manage_members"]


def can_manage_billing(auth: AuthContext) -> bool:
    """
    Check if user can manage billing.

    Rules:
    - Owner: Yes
    - Everyone else: No

    Args:
        auth: Authenticated user context

    Returns:
        True if user can manage billing
    """
    user_role = Role.from_string(auth.role)
    caps = get_role_capabilities(user_role)
    return caps["can_manage_billing"]


def can_delete_org(auth: AuthContext) -> bool:
    """
    Check if user can delete the organization.

    Rules:
    - Owner: Yes
    - Everyone else: No

    Args:
        auth: Authenticated user context

    Returns:
        True if user can delete org
    """
    user_role = Role.from_string(auth.role)
    caps = get_role_capabilities(user_role)
    return caps["can_delete_org"]


def get_user_permissions(auth: AuthContext) -> dict[str, bool]:
    """
    Get complete permission matrix for current user.

    Useful for frontend to show/hide UI elements.

    Args:
        auth: Authenticated user context

    Returns:
        Dictionary of all permissions

    Example:
        perms = get_user_permissions(auth)
        if perms["can_manage_billing"]:
            # Show billing settings
            ...
    """
    user_role = Role.from_string(auth.role)
    return get_role_capabilities(user_role)


def filter_resources_by_permission(
    auth: AuthContext,
    resources: list[Any],
    permission: str = "view",
) -> list[Any]:
    """
    Filter list of resources based on user permissions.

    Args:
        auth: Authenticated user context
        resources: List of resource objects
        permission: Permission to check ("view", "edit", "delete")

    Returns:
        Filtered list of resources user has permission for

    Example:
        documents = await repo.list_by_org(org_id)
        visible_docs = filter_resources_by_permission(auth, documents, "view")
    """
    permission_checks = {
        "view": can_view_resource,
        "edit": can_edit_resource,
        "delete": can_delete_resource,
    }

    check_func = permission_checks.get(permission)
    if not check_func:
        raise ValueError(f"Invalid permission: {permission}")

    return [r for r in resources if check_func(auth, r)]


def log_permission_check(
    auth: AuthContext,
    action: str,
    resource_type: str,
    resource_id: str | UUID | None = None,
    allowed: bool = True,
) -> None:
    """
    Log permission check for audit trail.

    Args:
        auth: Authenticated user context
        action: Action being performed (view, edit, delete, etc.)
        resource_type: Type of resource (document, org, user, etc.)
        resource_id: ID of specific resource (optional)
        allowed: Whether permission was granted
    """
    log_level = logging.INFO if allowed else logging.WARNING

    logger.log(
        log_level,
        f"Permission check: {action} {resource_type} - {'allowed' if allowed else 'denied'}",
        extra={
            "user_id": str(auth.user_id),
            "org_id": str(auth.org_id),
            "role": auth.role,
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "allowed": allowed,
            "request_id": auth.request_id,
        },
    )
