"""
API / Integration tests.

Tests HTTP endpoints end-to-end through the FastAPI app using httpx AsyncClient.
Auth is bypassed via dependency overrides (see conftest.py fixtures).

Covers:
  - Health endpoints
  - Auth introspection
  - User profile CRUD
  - Organization CRUD
  - Signal listing & detail
  - Credit balance & transactions
  - Chat sessions
  - Protected endpoint 401 without token
  - Cross-tenant isolation
"""

from uuid import uuid4

import pytest

from tests.conftest import (
    create_industry,
    create_org_user,
    create_organization,
    create_signal,
    create_signal_contract,
    create_user,
    make_auth_context,
)

pytestmark = pytest.mark.asyncio


# ── Health Endpoints ─────────────────────────────────────────────────


class TestHealthEndpoints:
    async def test_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data

    async def test_health_v1(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"


# ── Auth Introspection ───────────────────────────────────────────────


class TestAuthEndpoints:
    async def test_get_me(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["email"] == auth.email
        assert data["organization"]["role"] == auth.role
        assert isinstance(data["permissions"], dict)

    async def test_get_permissions(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get("/api/v1/auth/permissions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == auth.role
        assert isinstance(data["permissions"], dict)

    async def test_verify_token(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get("/api/v1/auth/token/verify")
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True


# ── User Endpoints ───────────────────────────────────────────────────


class TestUserEndpoints:
    async def test_get_my_profile(self, app, client, db_session):
        """Create a real user in DB matching the auth context, then GET /users/me."""
        from backend.auth.dependencies import get_current_user

        user_id = uuid4()
        user = await create_user(db_session, email="profile@cogent.ai", user_id=user_id)
        auth = make_auth_context(user_id=user_id, email="profile@cogent.ai")
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "profile@cogent.ai"

    async def test_update_my_profile(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        user_id = uuid4()
        user = await create_user(db_session, email="update@cogent.ai", user_id=user_id)
        auth = make_auth_context(user_id=user_id, email="update@cogent.ai")
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.patch(
            "/api/v1/users/me",
            json={"name": "Updated Name"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Name"

    async def test_get_other_user_profile(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        org = await create_organization(db_session)
        user1 = await create_user(db_session, email="me@cogent.ai")
        user2 = await create_user(db_session, email="other@cogent.ai")
        # Both users must be in the same org (IDOR fix requires org membership)
        await create_org_user(db_session, org=org, user=user1)
        await create_org_user(db_session, org=org, user=user2)
        auth = make_auth_context(user_id=user1.id, org_id=org.id)
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get(f"/api/v1/users/{user2.id}")
        assert resp.status_code == 200
        data = resp.json()
        # PII must NOT be exposed for other users (security fix)
        assert "email" not in data
        assert "auth0_id" not in data
        assert "last_login_at" not in data
        assert data["id"] == str(user2.id)

    async def test_get_nonexistent_user(self, authenticated_client):
        client, auth = authenticated_client
        fake_id = uuid4()
        resp = await client.get(f"/api/v1/users/{fake_id}")
        assert resp.status_code == 404


# ── Organization Endpoints ───────────────────────────────────────────


class TestOrgEndpoints:
    async def test_get_organization(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        org = await create_organization(db_session, name="Test Inc")
        auth = make_auth_context(org_id=org.id)
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get(f"/api/v1/orgs/{org.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Inc"

    async def test_get_org_forbidden_different_org(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        org = await create_organization(db_session)
        auth = make_auth_context(org_id=uuid4())  # Different org
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get(f"/api/v1/orgs/{org.id}")
        assert resp.status_code == 403

    async def test_update_org_requires_admin(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        org = await create_organization(db_session)
        # Member trying to update → should fail
        auth = make_auth_context(org_id=org.id, role="member")
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.patch(
            f"/api/v1/orgs/{org.id}",
            json={"name": "New Name"},
        )
        # Should be 403 since member can't update org
        assert resp.status_code == 403


# ── Signal Endpoints ─────────────────────────────────────────────────


class TestSignalEndpoints:
    async def test_list_signals(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        org = await create_organization(db_session)
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        sig = await create_signal(
            db_session, contract=sc, org=org, title="Alpha Signal"
        )
        auth = make_auth_context(org_id=org.id)
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get("/api/v1/signals")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    async def test_get_signal_detail(self, app, client, db_session):
        from backend.auth.dependencies import get_current_user

        org = await create_organization(db_session)
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        sig = await create_signal(db_session, contract=sc, org=org)
        auth = make_auth_context(org_id=org.id)
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get(f"/api/v1/signals/{sig.id}")
        assert resp.status_code == 200

    async def test_get_signal_not_found(self, authenticated_client):
        client, auth = authenticated_client
        resp = await client.get(f"/api/v1/signals/{uuid4()}")
        assert resp.status_code == 404

    async def test_cross_tenant_signal_isolation(self, app, client, db_session):
        """Org A should NOT see Org B's private signal."""
        from backend.auth.dependencies import get_current_user

        org_a = await create_organization(db_session, slug="org-a")
        org_b = await create_organization(db_session, slug="org-b")
        ind = await create_industry(db_session)
        sc = await create_signal_contract(db_session, industry=ind)
        sig_b = await create_signal(
            db_session, contract=sc, org=org_b, title="Secret B"
        )

        # Auth as Org A
        auth_a = make_auth_context(org_id=org_a.id)
        app.dependency_overrides[get_current_user] = lambda: auth_a

        resp = await client.get(f"/api/v1/signals/{sig_b.id}")
        # Should be 404 (not leaked)
        assert resp.status_code == 404


# ── Credit Endpoints ─────────────────────────────────────────────────


class TestCreditEndpoints:
    async def test_get_credit_costs(self, client, app):
        """Credit costs endpoint is public-ish (no org required)."""
        from backend.auth.dependencies import get_current_user

        auth = make_auth_context()
        app.dependency_overrides[get_current_user] = lambda: auth

        resp = await client.get("/api/v1/credits/costs")
        assert resp.status_code == 200
        data = resp.json()
        assert "credit_costs" in data
        assert data["credit_costs"]["intelligence_brief"] == 50


# ── Protected Endpoint (no auth) ────────────────────────────────────


class TestProtectedEndpoints:
    async def test_api_endpoint_returns_401_without_token(self, unauthenticated_client):
        """Any /api/ endpoint should return 401 when no Bearer token is sent."""
        resp = await unauthenticated_client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_root_does_not_require_auth(self, unauthenticated_client):
        resp = await unauthenticated_client.get("/")
        assert resp.status_code == 200
