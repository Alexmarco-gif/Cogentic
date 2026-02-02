"""
Authentication & Authorization Module

This module provides JWT verification, RBAC, and multi-tenant authorization
for the Cogent API.

Key Components:
- JWT verification with Auth0 JWKS
- Role-based access control (RBAC)
- Multi-tenant authorization guards
- Request context injection
"""

from backend.auth.dependencies import get_current_user, get_optional_user
from backend.auth.enums import Role, get_role_capabilities, role_hierarchy_check
from backend.auth.exceptions import (
    AuthError,
    ForbiddenError,
    TokenExpiredError,
    InvalidTokenError,
    InsufficientRoleError,
    NotOrgMemberError,
    NotResourceOwnerError,
    FeatureDisabledError,
)
from backend.auth.guards import (
    require_role,
    require_owner,
    require_admin,
    require_member,
    require_org_membership,
    require_resource_ownership,
    can_manage_member,
    require_can_manage_member,
    require_feature,
)
from backend.auth.permissions import (
    can_view_resource,
    can_edit_resource,
    can_delete_resource,
    can_create_resource,
    can_manage_members,
    can_manage_billing,
    can_delete_org,
    get_user_permissions,
    filter_resources_by_permission,
)
from backend.auth.schemas import AuthContext, JWTClaims, TokenPayload

__all__ = [
    # Dependencies
    "get_current_user",
    "get_optional_user",
    # Enums
    "Role",
    "role_hierarchy_check",
    "get_role_capabilities",
    # Exceptions
    "AuthError",
    "ForbiddenError",
    "TokenExpiredError",
    "InvalidTokenError",
    "InsufficientRoleError",
    "NotOrgMemberError",
    "NotResourceOwnerError",
    "FeatureDisabledError",
    # Guards
    "require_role",
    "require_owner",
    "require_admin",
    "require_member",
    "require_org_membership",
    "require_resource_ownership",
    "can_manage_member",
    "require_feature",
    "require_can_manage_member",
    # Permissions
    "can_view_resource",
    "can_edit_resource",
    "can_delete_resource",
    "can_create_resource",
    "can_manage_members",
    "can_manage_billing",
    "can_delete_org",
    "get_user_permissions",
    "filter_resources_by_permission",
    # Schemas
    "AuthContext",
    "JWTClaims",
    "TokenPayload",
]
