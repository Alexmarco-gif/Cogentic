"""
Unit tests for authorization guards and permissions.

Tests RBAC enforcement, role hierarchy, and permission checks.
"""

import pytest
from uuid import uuid4, UUID

from backend.auth.enums import Role, role_hierarchy_check, get_role_capabilities
from backend.auth.exceptions import (
    InsufficientRoleError,
    NotOrgMemberError,
    NotResourceOwnerError,
    ForbiddenError,
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
)
from backend.auth.schemas import AuthContext
from datetime import datetime, timedelta


# Test fixtures
def create_auth_context(role: str = "member", org_id: UUID | None = None) -> AuthContext:
    """Helper to create test AuthContext"""
    if org_id is None:
        org_id = uuid4()
    
    return AuthContext(
        user_id=uuid4(),
        auth0_id="auth0|test123",
        email="test@example.com",
        org_id=org_id,
        role=role,
        plan="free",
        token_expires_at=datetime.utcnow() + timedelta(hours=1),
    )


class MockResource:
    """Mock resource for testing"""
    def __init__(self, owner_id: UUID, visibility: str = "private", shared_with: list = None):
        self.id = uuid4()
        self.owner_id = owner_id
        self.visibility = visibility
        self.shared_with = shared_with or []


class TestRoleEnum:
    """Test Role enum and hierarchy"""
    
    def test_role_hierarchy(self):
        """Test role hierarchy ordering"""
        assert Role.OWNER > Role.ADMIN
        assert Role.ADMIN > Role.MEMBER
        assert Role.MEMBER > Role.VIEWER
        
        assert Role.OWNER >= Role.OWNER
        assert Role.ADMIN >= Role.MEMBER
    
    def test_role_from_string(self):
        """Test string to enum conversion"""
        assert Role.from_string("owner") == Role.OWNER
        assert Role.from_string("ADMIN") == Role.ADMIN
        assert Role.from_string("  member  ") == Role.MEMBER
        
        with pytest.raises(ValueError, match="Invalid role"):
            Role.from_string("invalid")
    
    def test_role_to_string(self):
        """Test enum to string conversion"""
        assert Role.OWNER.to_string() == "owner"
        assert Role.ADMIN.to_string() == "admin"
        assert Role.MEMBER.to_string() == "member"
        assert Role.VIEWER.to_string() == "viewer"
    
    def test_role_all_roles(self):
        """Test getting all roles"""
        roles = Role.all_roles()
        assert roles == ["viewer", "member", "admin", "owner"]


class TestRoleHierarchyCheck:
    """Test role hierarchy checking function"""
    
    def test_hierarchy_check_with_strings(self):
        """Test role hierarchy with string inputs"""
        assert role_hierarchy_check("owner", "admin") is True
        assert role_hierarchy_check("admin", "member") is True
        assert role_hierarchy_check("member", "viewer") is True
        
        assert role_hierarchy_check("member", "admin") is False
        assert role_hierarchy_check("viewer", "member") is False
    
    def test_hierarchy_check_with_enums(self):
        """Test role hierarchy with enum inputs"""
        assert role_hierarchy_check(Role.OWNER, Role.ADMIN) is True
        assert role_hierarchy_check(Role.MEMBER, Role.OWNER) is False
    
    def test_hierarchy_check_equal_roles(self):
        """Test role hierarchy with equal roles"""
        assert role_hierarchy_check("admin", "admin") is True
        assert role_hierarchy_check(Role.MEMBER, Role.MEMBER) is True


class TestGetRoleCapabilities:
    """Test role capabilities matrix"""
    
    def test_viewer_capabilities(self):
        """Test viewer has minimal capabilities"""
        caps = get_role_capabilities(Role.VIEWER)
        assert caps["can_view"] is True
        assert caps["can_create"] is False
        assert caps["can_edit_own"] is False
        assert caps["can_manage_members"] is False
    
    def test_member_capabilities(self):
        """Test member can create and edit own"""
        caps = get_role_capabilities(Role.MEMBER)
        assert caps["can_view"] is True
        assert caps["can_create"] is True
        assert caps["can_edit_own"] is True
        assert caps["can_edit_all"] is False
        assert caps["can_manage_members"] is False
    
    def test_admin_capabilities(self):
        """Test admin can edit all but not manage billing"""
        caps = get_role_capabilities(Role.ADMIN)
        assert caps["can_edit_all"] is True
        assert caps["can_delete_all"] is True
        assert caps["can_manage_members"] is True
        assert caps["can_manage_billing"] is False
        assert caps["can_delete_org"] is False
    
    def test_owner_capabilities(self):
        """Test owner has full capabilities"""
        caps = get_role_capabilities(Role.OWNER)
        assert caps["can_view"] is True
        assert caps["can_edit_all"] is True
        assert caps["can_manage_members"] is True
        assert caps["can_manage_billing"] is True
        assert caps["can_delete_org"] is True


class TestRequireRole:
    """Test require_role guard"""
    
    def test_sufficient_role_passes(self):
        """Test user with sufficient role passes"""
        auth = create_auth_context(role="admin")
        
        # Should not raise
        require_role(auth, Role.MEMBER)
        require_role(auth, "member")
    
    def test_insufficient_role_fails(self):
        """Test user with insufficient role fails"""
        auth = create_auth_context(role="member")
        
        with pytest.raises(InsufficientRoleError) as exc_info:
            require_role(auth, Role.ADMIN)
        
        assert exc_info.value.details["required_role"] == "admin"
        assert exc_info.value.details["current_role"] == "member"
    
    def test_equal_role_passes(self):
        """Test user with exact role passes"""
        auth = create_auth_context(role="admin")
        require_role(auth, Role.ADMIN)


class TestRequireOrgMembership:
    """Test require_org_membership guard"""
    
    def test_same_org_passes(self):
        """Test user in same org passes"""
        org_id = uuid4()
        auth = create_auth_context(role="member", org_id=org_id)
        
        # Should not raise
        require_org_membership(auth, org_id)
    
    def test_different_org_fails(self):
        """Test user in different org fails"""
        auth = create_auth_context(role="member", org_id=uuid4())
        different_org = uuid4()
        
        with pytest.raises(NotOrgMemberError):
            require_org_membership(auth, different_org)


class TestRequireResourceOwnership:
    """Test require_resource_ownership guard"""
    
    def test_owner_can_access(self):
        """Test resource owner can access"""
        auth = create_auth_context(role="member")
        resource = MockResource(owner_id=auth.user_id)
        
        # Should not raise
        require_resource_ownership(auth, resource, "document")
    
    def test_non_owner_member_cannot_access(self):
        """Test non-owner member cannot access"""
        auth = create_auth_context(role="member")
        resource = MockResource(owner_id=uuid4())
        
        with pytest.raises(NotResourceOwnerError):
            require_resource_ownership(auth, resource, "document")
    
    def test_admin_can_access_with_allow_admin(self):
        """Test admin can access any resource with allow_admin=True"""
        auth = create_auth_context(role="admin")
        resource = MockResource(owner_id=uuid4())
        
        # Should not raise
        require_resource_ownership(auth, resource, "document", allow_admin=True)
    
    def test_admin_cannot_access_with_allow_admin_false(self):
        """Test admin cannot access with allow_admin=False"""
        auth = create_auth_context(role="admin")
        resource = MockResource(owner_id=uuid4())
        
        with pytest.raises(NotResourceOwnerError):
            require_resource_ownership(auth, resource, "document", allow_admin=False)
    
    def test_owner_role_can_access_any_resource(self):
        """Test Owner role can access any resource"""
        auth = create_auth_context(role="owner")
        resource = MockResource(owner_id=uuid4())
        
        # Should not raise
        require_resource_ownership(auth, resource, "document", allow_admin=True)


class TestShorthandGuards:
    """Test shorthand guard functions"""
    
    def test_require_owner(self):
        """Test require_owner shorthand"""
        owner_auth = create_auth_context(role="owner")
        admin_auth = create_auth_context(role="admin")
        
        require_owner(owner_auth)  # Should not raise
        
        with pytest.raises(InsufficientRoleError):
            require_owner(admin_auth)
    
    def test_require_admin(self):
        """Test require_admin shorthand"""
        owner_auth = create_auth_context(role="owner")
        admin_auth = create_auth_context(role="admin")
        member_auth = create_auth_context(role="member")
        
        require_admin(owner_auth)  # Should not raise
        require_admin(admin_auth)  # Should not raise
        
        with pytest.raises(InsufficientRoleError):
            require_admin(member_auth)
    
    def test_require_member(self):
        """Test require_member shorthand"""
        admin_auth = create_auth_context(role="admin")
        member_auth = create_auth_context(role="member")
        viewer_auth = create_auth_context(role="viewer")
        
        require_member(admin_auth)  # Should not raise
        require_member(member_auth)  # Should not raise
        
        with pytest.raises(InsufficientRoleError):
            require_member(viewer_auth)


class TestCanManageMember:
    """Test member management permissions"""
    
    def test_owner_can_manage_all(self):
        """Test owner can manage all roles"""
        auth = create_auth_context(role="owner")
        
        assert can_manage_member(auth, "owner") is True
        assert can_manage_member(auth, "admin") is True
        assert can_manage_member(auth, "member") is True
        assert can_manage_member(auth, "viewer") is True
    
    def test_admin_can_manage_members_and_viewers(self):
        """Test admin can manage members and viewers only"""
        auth = create_auth_context(role="admin")
        
        assert can_manage_member(auth, "owner") is False
        assert can_manage_member(auth, "admin") is False
        assert can_manage_member(auth, "member") is True
        assert can_manage_member(auth, "viewer") is True
    
    def test_member_cannot_manage_anyone(self):
        """Test member cannot manage anyone"""
        auth = create_auth_context(role="member")
        
        assert can_manage_member(auth, "member") is False
        assert can_manage_member(auth, "viewer") is False


class TestPermissions:
    """Test permission checking functions"""
    
    def test_can_create_resource(self):
        """Test can_create_resource permission"""
        assert can_create_resource(create_auth_context("viewer")) is False
        assert can_create_resource(create_auth_context("member")) is True
        assert can_create_resource(create_auth_context("admin")) is True
        assert can_create_resource(create_auth_context("owner")) is True
    
    def test_can_manage_members(self):
        """Test can_manage_members permission"""
        assert can_manage_members(create_auth_context("viewer")) is False
        assert can_manage_members(create_auth_context("member")) is False
        assert can_manage_members(create_auth_context("admin")) is True
        assert can_manage_members(create_auth_context("owner")) is True
    
    def test_can_manage_billing(self):
        """Test can_manage_billing permission"""
        assert can_manage_billing(create_auth_context("viewer")) is False
        assert can_manage_billing(create_auth_context("member")) is False
        assert can_manage_billing(create_auth_context("admin")) is False
        assert can_manage_billing(create_auth_context("owner")) is True
    
    def test_can_delete_org(self):
        """Test can_delete_org permission"""
        assert can_delete_org(create_auth_context("admin")) is False
        assert can_delete_org(create_auth_context("owner")) is True


class TestResourcePermissions:
    """Test resource-level permissions"""
    
    def test_can_view_private_resource(self):
        """Test viewing private resources"""
        auth = create_auth_context("member")
        own_resource = MockResource(auth.user_id, "private")
        other_resource = MockResource(uuid4(), "private")
        
        assert can_view_resource(auth, own_resource) is True
        assert can_view_resource(auth, other_resource) is False
    
    def test_can_view_shared_resource(self):
        """Test viewing shared resources"""
        auth = create_auth_context("member")
        shared_resource = MockResource(
            uuid4(),
            "shared",
            shared_with=[str(auth.user_id)]
        )
        not_shared_resource = MockResource(
            uuid4(),
            "shared",
            shared_with=[]
        )
        
        assert can_view_resource(auth, shared_resource) is True
        assert can_view_resource(auth, not_shared_resource) is False
    
    def test_admin_can_view_all(self):
        """Test admin can view all resources"""
        auth = create_auth_context("admin")
        private_resource = MockResource(uuid4(), "private")
        
        assert can_view_resource(auth, private_resource) is True
    
    def test_can_edit_own_resource(self):
        """Test editing own resources"""
        auth = create_auth_context("member")
        own_resource = MockResource(auth.user_id)
        other_resource = MockResource(uuid4())
        
        assert can_edit_resource(auth, own_resource) is True
        assert can_edit_resource(auth, other_resource) is False
    
    def test_admin_can_edit_all(self):
        """Test admin can edit all resources"""
        auth = create_auth_context("admin")
        other_resource = MockResource(uuid4())
        
        assert can_edit_resource(auth, other_resource) is True
    
    def test_viewer_cannot_edit(self):
        """Test viewer cannot edit anything"""
        auth = create_auth_context("viewer")
        own_resource = MockResource(auth.user_id)
        
        assert can_edit_resource(auth, own_resource) is False


class TestGetUserPermissions:
    """Test get_user_permissions utility"""
    
    def test_get_permissions_returns_complete_matrix(self):
        """Test getting complete permission matrix"""
        auth = create_auth_context("admin")
        perms = get_user_permissions(auth)
        
        assert isinstance(perms, dict)
        assert "can_view" in perms
        assert "can_create" in perms
        assert "can_manage_members" in perms
        assert perms["can_manage_members"] is True
        assert perms["can_manage_billing"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
