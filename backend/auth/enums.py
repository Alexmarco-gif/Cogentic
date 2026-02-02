"""
Role enums and hierarchy for RBAC (Role-Based Access Control).

Defines the role hierarchy used throughout the application:
Owner > Admin > Member > Viewer
"""

from enum import IntEnum


class Role(IntEnum):
    """
    User roles with hierarchical ordering.
    
    Higher numeric value = higher privilege level.
    This allows simple comparison operations (>=, >, etc.)
    
    Hierarchy:
    - Owner (4): Full control - billing, delete org, manage all
    - Admin (3): High control - manage members (non-owners), all resources
    - Member (2): Standard access - create/edit own resources, view team resources
    - Viewer (1): Read-only - view resources only, no mutations
    
    Usage:
        if Role[user.role] >= Role.ADMIN:
            # User is Admin or Owner
            ...
    """
    
    VIEWER = 1
    MEMBER = 2
    ADMIN = 3
    OWNER = 4
    
    @classmethod
    def from_string(cls, role_str: str) -> "Role":
        """
        Convert string role to enum.
        
        Args:
            role_str: Role string (case-insensitive)
            
        Returns:
            Role enum value
            
        Raises:
            ValueError: If role string invalid
            
        Examples:
            >>> Role.from_string("admin")
            Role.ADMIN
            >>> Role.from_string("OWNER")
            Role.OWNER
        """
        role_map = {
            "viewer": cls.VIEWER,
            "member": cls.MEMBER,
            "admin": cls.ADMIN,
            "owner": cls.OWNER,
        }
        
        normalized = role_str.lower().strip()
        if normalized not in role_map:
            raise ValueError(
                f"Invalid role: {role_str}. "
                f"Must be one of: viewer, member, admin, owner"
            )
        
        return role_map[normalized]
    
    def to_string(self) -> str:
        """
        Convert enum to lowercase string.
        
        Returns:
            Role name in lowercase
            
        Examples:
            >>> Role.ADMIN.to_string()
            'admin'
        """
        return self.name.lower()
    
    @classmethod
    def all_roles(cls) -> list[str]:
        """Get list of all role names (lowercase)"""
        return ["viewer", "member", "admin", "owner"]
    
    def __str__(self) -> str:
        return self.name.lower()
    
    def __repr__(self) -> str:
        return f"Role.{self.name}"


def role_hierarchy_check(user_role: str | Role, required_role: str | Role) -> bool:
    """
    Check if user role meets or exceeds required role.
    
    Args:
        user_role: User's current role (string or enum)
        required_role: Minimum required role (string or enum)
        
    Returns:
        True if user role >= required role
        
    Examples:
        >>> role_hierarchy_check("admin", "member")
        True
        >>> role_hierarchy_check("member", "admin")
        False
        >>> role_hierarchy_check("owner", "owner")
        True
    """
    # Convert strings to enums
    if isinstance(user_role, str):
        user_role = Role.from_string(user_role)
    if isinstance(required_role, str):
        required_role = Role.from_string(required_role)
    
    return user_role >= required_role


def get_role_capabilities(role: str | Role) -> dict[str, bool]:
    """
    Get capability matrix for a role.
    
    Args:
        role: Role to check (string or enum)
        
    Returns:
        Dictionary of capabilities and their availability
        
    Example:
        >>> get_role_capabilities("admin")
        {
            "can_view": True,
            "can_create": True,
            "can_edit_own": True,
            "can_edit_all": True,
            "can_delete_own": True,
            "can_delete_all": True,
            "can_manage_members": True,
            "can_manage_billing": False,
            "can_delete_org": False,
        }
    """
    if isinstance(role, str):
        role = Role.from_string(role)
    
    # Base capabilities by role
    capabilities = {
        Role.VIEWER: {
            "can_view": True,
            "can_create": False,
            "can_edit_own": False,
            "can_edit_all": False,
            "can_delete_own": False,
            "can_delete_all": False,
            "can_manage_members": False,
            "can_manage_billing": False,
            "can_delete_org": False,
            "can_change_owner_role": False,
        },
        Role.MEMBER: {
            "can_view": True,
            "can_create": True,
            "can_edit_own": True,
            "can_edit_all": False,
            "can_delete_own": True,
            "can_delete_all": False,
            "can_manage_members": False,
            "can_manage_billing": False,
            "can_delete_org": False,
            "can_change_owner_role": False,
        },
        Role.ADMIN: {
            "can_view": True,
            "can_create": True,
            "can_edit_own": True,
            "can_edit_all": True,
            "can_delete_own": True,
            "can_delete_all": True,
            "can_manage_members": True,  # But not owners
            "can_manage_billing": False,
            "can_delete_org": False,
            "can_change_owner_role": False,
        },
        Role.OWNER: {
            "can_view": True,
            "can_create": True,
            "can_edit_own": True,
            "can_edit_all": True,
            "can_delete_own": True,
            "can_delete_all": True,
            "can_manage_members": True,
            "can_manage_billing": True,
            "can_delete_org": True,
            "can_change_owner_role": True,
        },
    }
    
    return capabilities[role]
