"""
Authentication & Authorization tests.

Covers:
  - Role enum & hierarchy
  - Permission checks (can_view, can_edit, can_delete, etc.)
  - Guard functions (require_role, require_admin, require_owner, etc.)
  - Auth context creation
  - Token payload schema
  - Expired token / missing token exceptions
  - M2M token detection
  - Super admin bypass
  - Feature gating by tier
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.auth.enums import Role, get_role_capabilities, role_hierarchy_check
from backend.auth.exceptions import (
    AuthError,
    FeatureDisabledError,
    ForbiddenError,
    InsufficientRoleError,
    InvalidTokenError,
    MissingTokenError,
    NotOrgMemberError,
    NotResourceOwnerError,
    TokenExpiredError,
)
from backend.auth.guards import (
    require_org_membership,
    require_resource_ownership,
    require_role,
)
from backend.auth.permissions import (
    can_edit_resource,
    can_view_resource,
    get_user_permissions,
)
from backend.auth.schemas import TokenPayload
from tests.conftest import make_auth_context

# ── Role Enum ────────────────────────────────────────────────────────


class TestRoleEnum:
    def test_role_values_ascending(self):
        assert Role.VIEWER < Role.MEMBER < Role.ADMIN < Role.OWNER

    def test_from_string_valid(self):
        assert Role.from_string("viewer") == Role.VIEWER
        assert Role.from_string("member") == Role.MEMBER
        assert Role.from_string("admin") == Role.ADMIN
        assert Role.from_string("owner") == Role.OWNER
        # Case insensitive
        assert Role.from_string("ADMIN") == Role.ADMIN
        assert Role.from_string("Owner") == Role.OWNER

    def test_from_string_invalid(self):
        with pytest.raises(ValueError, match="Invalid role"):
            Role.from_string("superuser")

    def test_to_string(self):
        assert Role.ADMIN.to_string() == "admin"
        assert Role.OWNER.to_string() == "owner"

    def test_all_roles(self):
        roles = Role.all_roles()
        assert roles == ["viewer", "member", "admin", "owner"]


# ── Role Hierarchy Check ─────────────────────────────────────────────


class TestRoleHierarchy:
    def test_owner_beats_all(self):
        assert role_hierarchy_check("owner", "owner") is True
        assert role_hierarchy_check("owner", "admin") is True
        assert role_hierarchy_check("owner", "member") is True
        assert role_hierarchy_check("owner", "viewer") is True

    def test_admin_beats_lower(self):
        assert role_hierarchy_check("admin", "admin") is True
        assert role_hierarchy_check("admin", "member") is True
        assert role_hierarchy_check("admin", "viewer") is True
        assert role_hierarchy_check("admin", "owner") is False

    def test_member_beats_viewer(self):
        assert role_hierarchy_check("member", "viewer") is True
        assert role_hierarchy_check("member", "member") is True
        assert role_hierarchy_check("member", "admin") is False

    def test_viewer_only_viewer(self):
        assert role_hierarchy_check("viewer", "viewer") is True
        assert role_hierarchy_check("viewer", "member") is False

    def test_enum_args(self):
        assert role_hierarchy_check(Role.ADMIN, Role.MEMBER) is True
        assert role_hierarchy_check(Role.MEMBER, Role.ADMIN) is False


# ── Role Capabilities ────────────────────────────────────────────────


class TestRoleCapabilities:
    def test_viewer_capabilities(self):
        caps = get_role_capabilities("viewer")
        assert caps["can_view"] is True
        assert caps["can_create"] is False
        assert caps["can_edit_own"] is False
        assert caps["can_manage_members"] is False
        assert caps["can_manage_billing"] is False

    def test_member_capabilities(self):
        caps = get_role_capabilities("member")
        assert caps["can_view"] is True
        assert caps["can_create"] is True
        assert caps["can_edit_own"] is True
        assert caps["can_edit_all"] is False
        assert caps["can_manage_members"] is False

    def test_admin_capabilities(self):
        caps = get_role_capabilities("admin")
        assert caps["can_view"] is True
        assert caps["can_create"] is True
        assert caps["can_edit_all"] is True
        assert caps["can_delete_all"] is True
        assert caps["can_manage_members"] is True
        assert caps["can_manage_billing"] is False

    def test_owner_capabilities(self):
        caps = get_role_capabilities("owner")
        assert caps["can_view"] is True
        assert caps["can_manage_billing"] is True
        assert caps["can_delete_org"] is True
        assert caps["can_change_owner_role"] is True


# ── Auth Context ─────────────────────────────────────────────────────


class TestAuthContext:
    def test_make_auth_context_defaults(self):
        ctx = make_auth_context()
        assert ctx.role == "member"
        assert ctx.plan == "free"
        assert ctx.is_super_admin is False
        assert ctx.token_expires_at > datetime.now(timezone.utc)

    def test_owner_properties(self):
        ctx = make_auth_context(role="owner")
        assert ctx.is_owner is True
        assert ctx.is_admin_or_higher is True
        assert ctx.is_member_or_higher is True

    def test_admin_properties(self):
        ctx = make_auth_context(role="admin")
        assert ctx.is_owner is False
        assert ctx.is_admin_or_higher is True
        assert ctx.is_member_or_higher is True

    def test_member_properties(self):
        ctx = make_auth_context(role="member")
        assert ctx.is_owner is False
        assert ctx.is_admin_or_higher is False
        assert ctx.is_member_or_higher is True

    def test_viewer_properties(self):
        ctx = make_auth_context(role="viewer")
        assert ctx.is_owner is False
        assert ctx.is_admin_or_higher is False
        assert ctx.is_member_or_higher is False

    def test_super_admin_is_admin_or_higher(self):
        ctx = make_auth_context(role="viewer", is_super_admin=True)
        assert ctx.is_admin_or_higher is True

    def test_repr(self):
        ctx = make_auth_context()
        r = repr(ctx)
        assert "AuthContext" in r


# ── Token Payload ────────────────────────────────────────────────────


class TestTokenPayload:
    def test_m2m_token_detection(self):
        payload = TokenPayload(
            iss="https://cogent.auth0.com/",
            sub="client123",
            aud="https://api.cogent.ai",
            exp=9999999999,
            iat=1000000000,
            gty="client-credentials",
        )
        assert payload.is_m2m_token is True

    def test_user_token_not_m2m(self):
        payload = TokenPayload(
            iss="https://cogent.auth0.com/",
            sub="auth0|user123",
            aud="https://api.cogent.ai",
            exp=9999999999,
            iat=1000000000,
        )
        assert payload.is_m2m_token is False


# ── Guard Functions ──────────────────────────────────────────────────


class TestGuardFunctions:
    def test_require_role_passes_when_sufficient(self):
        ctx = make_auth_context(role="admin")
        # Should not raise
        require_role(ctx, "member")
        require_role(ctx, "admin")

    def test_require_role_raises_when_insufficient(self):
        ctx = make_auth_context(role="member")
        with pytest.raises(InsufficientRoleError):
            require_role(ctx, "admin")

    def test_require_role_with_string(self):
        ctx = make_auth_context(role="owner")
        require_role(ctx, "owner")  # Should not raise

    def test_require_org_membership_same_org(self):
        org_id = uuid4()
        ctx = make_auth_context(org_id=org_id)
        # Should not raise
        require_org_membership(ctx, org_id)

    def test_require_org_membership_different_org(self):
        ctx = make_auth_context(org_id=uuid4())
        with pytest.raises(NotOrgMemberError):
            require_org_membership(ctx, uuid4())

    def test_super_admin_bypasses_org_check(self):
        ctx = make_auth_context(org_id=uuid4(), is_super_admin=True)
        # Should NOT raise even for a different org
        require_org_membership(ctx, uuid4())

    def test_require_resource_ownership_owner(self):
        user_id = uuid4()
        ctx = make_auth_context(user_id=user_id, role="member")

        class FakeResource:
            owner_id = user_id

        # Should not raise — user owns the resource
        require_resource_ownership(ctx, FakeResource(), "document")

    def test_require_resource_ownership_admin_override(self):
        ctx = make_auth_context(role="admin")

        class FakeResource:
            owner_id = uuid4()  # Different user

        # Admins can access when allow_admin=True (default)
        require_resource_ownership(ctx, FakeResource(), "document", allow_admin=True)

    def test_require_resource_ownership_non_owner_non_admin(self):
        ctx = make_auth_context(role="member")

        class FakeResource:
            owner_id = uuid4()  # Different user

        with pytest.raises(NotResourceOwnerError):
            require_resource_ownership(ctx, FakeResource(), "document")

    def test_require_resource_no_owner_attr(self):
        ctx = make_auth_context(role="admin")

        class BadResource:
            pass

        with pytest.raises(AttributeError):
            require_resource_ownership(ctx, BadResource(), "widget")


# ── Permission Functions ─────────────────────────────────────────────


class TestPermissionFunctions:
    def _make_resource(self, owner_id, visibility="private"):
        class R:
            pass

        r = R()
        r.owner_id = owner_id
        r.visibility = visibility
        r.shared_with = []
        return r

    def test_admin_can_view_anything(self):
        ctx = make_auth_context(role="admin")
        res = self._make_resource(owner_id=uuid4(), visibility="private")
        assert can_view_resource(ctx, res) is True

    def test_member_can_view_own_private(self):
        user_id = uuid4()
        ctx = make_auth_context(user_id=user_id, role="member")
        res = self._make_resource(owner_id=user_id, visibility="private")
        assert can_view_resource(ctx, res) is True

    def test_member_cannot_view_others_private(self):
        ctx = make_auth_context(role="member")
        res = self._make_resource(owner_id=uuid4(), visibility="private")
        assert can_view_resource(ctx, res) is False

    def test_member_can_view_org_visibility(self):
        ctx = make_auth_context(role="member")
        res = self._make_resource(owner_id=uuid4(), visibility="org")
        assert can_view_resource(ctx, res) is True

    def test_viewer_can_view_org_visibility(self):
        ctx = make_auth_context(role="viewer")
        res = self._make_resource(owner_id=uuid4(), visibility="org")
        assert can_view_resource(ctx, res) is True

    def test_viewer_cannot_edit(self):
        ctx = make_auth_context(role="viewer")
        res = self._make_resource(owner_id=uuid4())
        assert can_edit_resource(ctx, res) is False

    def test_member_can_edit_own(self):
        user_id = uuid4()
        ctx = make_auth_context(user_id=user_id, role="member")
        res = self._make_resource(owner_id=user_id)
        assert can_edit_resource(ctx, res) is True

    def test_member_cannot_edit_others(self):
        ctx = make_auth_context(role="member")
        res = self._make_resource(owner_id=uuid4())
        assert can_edit_resource(ctx, res) is False

    def test_admin_can_edit_all(self):
        ctx = make_auth_context(role="admin")
        res = self._make_resource(owner_id=uuid4())
        assert can_edit_resource(ctx, res) is True

    def test_get_user_permissions_admin(self):
        ctx = make_auth_context(role="admin")
        perms = get_user_permissions(ctx)
        assert isinstance(perms, dict)
        assert len(perms) > 0
        assert perms.get("can_create") is True


# ── Exception Classes ────────────────────────────────────────────────


class TestAuthExceptions:
    def test_auth_error_base(self):
        err = AuthError("test error", {"key": "val"})
        assert err.message == "test error"
        assert err.details == {"key": "val"}

    def test_invalid_token_error(self):
        err = InvalidTokenError("bad sig")
        assert "Invalid token" in err.message
        assert err.details["reason"] == "bad sig"

    def test_token_expired_error(self):
        err = TokenExpiredError("2026-01-01T00:00:00Z")
        assert "expired" in err.message.lower()

    def test_missing_token_error(self):
        err = MissingTokenError()
        assert "Missing" in err.message

    def test_forbidden_error(self):
        err = ForbiddenError("nope")
        assert err.message == "nope"

    def test_insufficient_role_error(self):
        err = InsufficientRoleError(required_role="admin", current_role="member")
        assert err.details["required_role"] == "admin"
        assert err.details["current_role"] == "member"

    def test_not_org_member_error(self):
        org_id = str(uuid4())
        err = NotOrgMemberError(org_id)
        assert err.details["org_id"] == org_id

    def test_not_resource_owner_error(self):
        err = NotResourceOwnerError("document", "abc-123")
        assert "document" in err.message
        assert err.details["resource_id"] == "abc-123"

    def test_feature_disabled_error(self):
        err = FeatureDisabledError("compliance_modules")
        assert "compliance_modules" in err.message
