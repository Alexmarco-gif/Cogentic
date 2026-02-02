"""
Phase 1 Integration Tests: Authentication & Authorization

Comprehensive end-to-end testing for:
- JWT token validation and custom claims
- Protected endpoint access control
- Organization-scoped data isolation
- Role-based permissions (RBAC)
- Rate limiting behavior
- Webhook signature verification
- Organization member CRUD operations
- API key authentication
- Feature flags with auth context

Test Strategy:
- Mock JWT tokens (fast, no Auth0 dependency)
- In-memory SQLite database (isolated, fast)
- Async test client (httpx.AsyncClient)
- Mocked JWKS endpoint (no external calls)

Expected Runtime: ~60 seconds for 50+ tests
"""

import pytest
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import UUID, uuid4
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.config import get_settings
from backend.database import get_db
from backend.models.base import Base
from backend.models.user import User
from backend.models.organization import Organization
from backend.models.org_user import OrgUser
from backend.models.api_key import APIKey

settings = get_settings()

# Test constants
TEST_SECRET_KEY = "test_secret_key_for_jwt_signing_do_not_use_in_production"
TEST_ORG_1_ID = uuid4()
TEST_ORG_2_ID = uuid4()
TEST_USER_1_ID = uuid4()
TEST_USER_2_ID = uuid4()
TEST_ADMIN_ID = uuid4()


# ============================================================================
# FIXTURES
# ============================================================================

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="function")
def test_db():
    """
    Create an in-memory SQLite database for testing.
    Uses synchronous SQLite since TestClient is synchronous.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture
def seed_test_data(test_db):
    """
    Seed database with test organizations, users, and memberships.

    Creates:
    - Org 1: user1 (owner), admin (admin), user2 (member)
    - Org 2: user2 (owner)
    """
    # Create organizations
    org1 = Organization(
        id=TEST_ORG_1_ID,
        name="Test Org 1",
        slug="test-org-1",
        billing_email="billing@org1.com",
    )
    org2 = Organization(
        id=TEST_ORG_2_ID,
        name="Test Org 2",
        slug="test-org-2",
        billing_email="billing@org2.com",
    )
    test_db.add(org1)
    test_db.add(org2)

    # Create users
    user1 = User(
        id=TEST_USER_1_ID,
        auth0_id="auth0|user1",
        email="user1@example.com",
        name="User One",
    )
    user2 = User(
        id=TEST_USER_2_ID,
        auth0_id="auth0|user2",
        email="user2@example.com",
        name="User Two",
    )
    admin = User(
        id=TEST_ADMIN_ID,
        auth0_id="auth0|admin",
        email="admin@example.com",
        name="Admin User",
    )
    test_db.add(user1)
    test_db.add(user2)
    test_db.add(admin)

    # Create memberships
    # Org1: user1=owner, admin=admin, user2=member
    test_db.add(OrgUser(org_id=TEST_ORG_1_ID, user_id=TEST_USER_1_ID, role="owner"))
    test_db.add(OrgUser(org_id=TEST_ORG_1_ID, user_id=TEST_ADMIN_ID, role="admin"))
    test_db.add(OrgUser(org_id=TEST_ORG_1_ID, user_id=TEST_USER_2_ID, role="member"))

    # Org2: user2=owner
    test_db.add(OrgUser(org_id=TEST_ORG_2_ID, user_id=TEST_USER_2_ID, role="owner"))

    test_db.commit()

    yield {
        "org1": org1,
        "org2": org2,
        "user1": user1,
        "user2": user2,
        "admin": admin,
    }


@pytest.fixture
def client(test_db):
    """
    FastAPI TestClient with database dependency override.
    """

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_redis():
    """Mock Redis client for rate limiting and idempotency tests"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.ping = AsyncMock(return_value=True)

    with patch("backend.redis_client.get_redis", return_value=redis):
        yield redis


@pytest.fixture
def mock_jwks():
    """
    Mock token verification to skip Auth0 JWKS fetching.
    Tokens will be decoded without signature verification for testing.
    """
    # Mock the verify_token function to bypass kid/JWKS validation
    async def mock_verify_token(token: str):
        # Decode without verification for testing
        from jose import jwt
        from backend.auth.schemas import TokenPayload

        payload = jwt.decode(
            token,
            TEST_SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_signature": False},
        )
        return TokenPayload(**payload)

    with patch("backend.auth.utils.verify_token", side_effect=mock_verify_token):
        yield


# ============================================================================
# TEST HELPERS
# ============================================================================


def create_test_token(
    user_id: UUID,
    auth0_id: str,
    email: str,
    org_id: UUID,
    role: str = "member",
    plan: str = "free",
    expired: bool = False,
    missing_claims: list[str] | None = None,
) -> str:
    """
    Create a mock JWT token for testing.

    Args:
        user_id: User UUID
        auth0_id: Auth0 user ID (e.g., "auth0|123")
        email: User email
        org_id: Organization UUID
        role: User role (viewer/member/admin/owner)
        plan: Subscription plan
        expired: Whether token should be expired
        missing_claims: List of custom claims to omit

    Returns:
        JWT token string
    """
    now = int(datetime.utcnow().timestamp())
    exp = now - 3600 if expired else now + 3600

    payload = {
        "iss": f"https://{settings.auth0_domain}/",
        "sub": auth0_id,
        "aud": settings.auth0_audience,
        "exp": exp,
        "iat": now,
        "email": email,
    }

    # Add custom claims (with namespace)
    missing = missing_claims or []
    namespace = "https://cogent-ai.com/"

    if "user_id" not in missing:
        payload[f"{namespace}user_id"] = str(user_id)

    if "org_id" not in missing:
        payload[f"{namespace}org_id"] = str(org_id)

    if "roles" not in missing:
        payload[f"{namespace}roles"] = [role]

    if "plan" not in missing:
        payload[f"{namespace}plan"] = plan

    return jwt.encode(payload, TEST_SECRET_KEY, algorithm="HS256")


def auth_headers(token: str) -> Dict[str, str]:
    """Create Authorization headers for requests"""
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# TEST SUITE 1: TOKEN VALIDATION
# ============================================================================


class TestTokenValidation:
    """Test JWT token extraction, verification, and claims validation"""

    def test_valid_token_accepted(self, client, mock_jwks, seed_test_data):
        """Valid token should grant access to protected endpoint"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            role="owner",
        )

        response = client.get("/api/v1/auth/me", headers=auth_headers(token))

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "user1@example.com"
        assert data["organization"]["id"] == str(TEST_ORG_1_ID)
        assert data["organization"]["role"] == "owner"

    def test_expired_token_rejected(self, client, mock_jwks):
        """Expired token should return 401"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            expired=True,
        )

        response = client.get("/api/v1/auth/me", headers=auth_headers(token))

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "Unauthorized"

    def test_missing_authorization_header(self, client):
        """Request without Authorization header should return 401"""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "Unauthorized"
        assert "invalid or expired" in data["message"].lower()

    def test_malformed_authorization_header(self, client):
        """Malformed Authorization header should return 401"""
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": "NotBearer token123"}
        )

        assert response.status_code == 401

    def test_invalid_token_format(self, client):
        """Invalid JWT format should return 401"""
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.valid.jwt"}
        )

        assert response.status_code == 401


# ============================================================================
# TEST SUITE 2: CUSTOM CLAIMS
# ============================================================================


class TestCustomClaims:
    """Test custom JWT claims extraction and validation"""

    def test_missing_org_id_claim_rejected(self, client, mock_jwks):
        """Token without org_id claim should return 401"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            missing_claims=["org_id"],
        )

        response = client.get("/api/v1/auth/me", headers=auth_headers(token))

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "Unauthorized"

    def test_missing_roles_claim_rejected(self, client, mock_jwks):
        """Token without roles claim should return 401"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            missing_claims=["roles"],
        )

        response = client.get("/api/v1/auth/me", headers=auth_headers(token))

        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "Unauthorized"

    def test_missing_plan_claim_rejected(self, client, mock_jwks):
        """Token without plan claim should return 401"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            missing_claims=["plan"],
        )

        response = client.get("/api/v1/auth/me", headers=auth_headers(token))

        assert response.status_code == 401

    def test_all_custom_claims_extracted(self, client, mock_jwks, seed_test_data):
        """All custom claims should be available in auth context"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            role="admin",
            plan="pro",
        )

        response = client.get("/api/v1/auth/me", headers=auth_headers(token))

        assert response.status_code == 200
        data = response.json()
        assert data["organization"]["role"] == "admin"
        assert data["subscription"]["plan"] == "pro"
        assert "permissions" in data


# ============================================================================
# TEST SUITE 3: PROTECTED ENDPOINTS
# ============================================================================


class TestProtectedEndpoints:
    """Test authentication requirements for protected endpoints"""

    def test_auth_me_endpoint(self, client, mock_jwks, seed_test_data):
        """GET /api/v1/auth/me should return user context"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            role="owner",
        )

        response = client.get("/api/v1/auth/me", headers=auth_headers(token))

        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "organization" in data
        assert "subscription" in data
        assert "permissions" in data
        assert "token" in data

    def test_auth_permissions_endpoint(self, client, mock_jwks, seed_test_data):
        """GET /api/v1/auth/permissions should return permission matrix"""
        token = create_test_token(
            user_id=TEST_ADMIN_ID,
            auth0_id="auth0|admin",
            email="admin@example.com",
            org_id=TEST_ORG_1_ID,
            role="admin",
        )

        response = client.get("/api/v1/auth/permissions", headers=auth_headers(token))

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert "permissions" in data
        assert data["permissions"]["can_manage_members"] is True

    def test_auth_token_verify_endpoint(self, client, mock_jwks, seed_test_data):
        """GET /api/v1/auth/token/verify should validate token"""
        token = create_test_token(
            user_id=TEST_USER_2_ID,
            auth0_id="auth0|user2",
            email="user2@example.com",
            org_id=TEST_ORG_2_ID,
            role="owner",
        )

        response = client.get("/api/v1/auth/token/verify", headers=auth_headers(token))

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user_id"] == str(TEST_USER_2_ID)
        assert data["org_id"] == str(TEST_ORG_2_ID)

    def test_unauthenticated_access_denied(self, client):
        """Protected endpoints should reject unauthenticated requests"""
        endpoints = [
            "/api/v1/auth/me",
            "/api/v1/auth/permissions",
            "/api/v1/auth/token/verify",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert (
                response.status_code == 401
            ), f"Endpoint {endpoint} should require auth"


# ============================================================================
# TEST SUITE 4: ORGANIZATION ISOLATION
# ============================================================================


class TestOrganizationIsolation:
    """Test that users can only access their organization's data"""

    def test_user_can_access_own_org(self, client, mock_jwks, seed_test_data):
        """User should access their own organization"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            role="owner",
        )

        response = client.get(
            f"/api/v1/orgs/{TEST_ORG_1_ID}", headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Org 1"

    def test_user_cannot_access_other_org(self, client, mock_jwks, seed_test_data):
        """User should not access another organization"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,  # User 1 is in Org 1
            role="owner",
        )

        # Try to access Org 2
        response = client.get(
            f"/api/v1/orgs/{TEST_ORG_2_ID}", headers=auth_headers(token)
        )

        assert response.status_code == 403
        assert "message" in response.json() or "detail" in response.json()

    def test_user_in_multiple_orgs(self, client, mock_jwks, seed_test_data):
        """User in multiple orgs should access based on token org_id"""
        # User 2 is in both Org 1 (member) and Org 2 (owner)

        # Token for Org 1
        token_org1 = create_test_token(
            user_id=TEST_USER_2_ID,
            auth0_id="auth0|user2",
            email="user2@example.com",
            org_id=TEST_ORG_1_ID,
            role="member",
        )

        response1 = client.get(
            f"/api/v1/orgs/{TEST_ORG_1_ID}", headers=auth_headers(token_org1)
        )
        assert response1.status_code == 200

        # Token for Org 2
        token_org2 = create_test_token(
            user_id=TEST_USER_2_ID,
            auth0_id="auth0|user2",
            email="user2@example.com",
            org_id=TEST_ORG_2_ID,
            role="owner",
        )

        response2 = client.get(
            f"/api/v1/orgs/{TEST_ORG_2_ID}", headers=auth_headers(token_org2)
        )
        assert response2.status_code == 200

    def test_org_member_list_isolated(self, client, mock_jwks, seed_test_data):
        """Users should only see members from their org"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            role="owner",
        )

        response = client.get(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/members", headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3  # user1, admin, user2 in Org1
        member_ids = [m["user_id"] for m in data["members"]]
        assert str(TEST_USER_1_ID) in member_ids
        assert str(TEST_ADMIN_ID) in member_ids
        assert str(TEST_USER_2_ID) in member_ids


# ============================================================================
# TEST SUITE 5: ROLE-BASED PERMISSIONS
# ============================================================================


class TestRoleBasedPermissions:
    """Test RBAC enforcement for different roles"""

    def test_owner_can_update_org(self, client, mock_jwks, seed_test_data):
        """Owner should be able to update organization"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            role="owner",
        )

        response = client.patch(
            f"/api/v1/orgs/{TEST_ORG_1_ID}",
            headers=auth_headers(token),
            json={"name": "Updated Org Name"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Org Name"

    def test_admin_can_update_org(self, client, mock_jwks, seed_test_data):
        """Admin should be able to update organization"""
        token = create_test_token(
            user_id=TEST_ADMIN_ID,
            auth0_id="auth0|admin",
            email="admin@example.com",
            org_id=TEST_ORG_1_ID,
            role="admin",
        )

        response = client.patch(
            f"/api/v1/orgs/{TEST_ORG_1_ID}",
            headers=auth_headers(token),
            json={"name": "Admin Updated Name"},
        )

        assert response.status_code == 200

    def test_member_cannot_update_org(self, client, mock_jwks, seed_test_data):
        """Member should not be able to update organization"""
        token = create_test_token(
            user_id=TEST_USER_2_ID,
            auth0_id="auth0|user2",
            email="user2@example.com",
            org_id=TEST_ORG_1_ID,
            role="member",
        )

        response = client.patch(
            f"/api/v1/orgs/{TEST_ORG_1_ID}",
            headers=auth_headers(token),
            json={"name": "Should Fail"},
        )

        assert response.status_code == 403

    @pytest.mark.skip(reason="Requires adding viewer to DB dynamically")
    def test_viewer_has_read_only_access(
        self, client, mock_jwks, seed_test_data, test_db
    ):
        """Viewer should only be able to read, not write"""
        # Add viewer to org
        viewer_id = uuid4()
        viewer = User(
            id=viewer_id,
            auth0_id="auth0|viewer",
            email="viewer@example.com",
            name="Viewer User",
        )
        test_db.add(viewer)
        test_db.add(OrgUser(org_id=TEST_ORG_1_ID, user_id=viewer_id, role="viewer"))
        test_db.commit()

        token = create_test_token(
            user_id=viewer_id,
            auth0_id="auth0|viewer",
            email="viewer@example.com",
            org_id=TEST_ORG_1_ID,
            role="viewer",
        )

        # Can read
        response_get = client.get(
            f"/api/v1/orgs/{TEST_ORG_1_ID}", headers=auth_headers(token)
        )
        assert response_get.status_code == 200

        # Cannot write
        response_patch = client.patch(
            f"/api/v1/orgs/{TEST_ORG_1_ID}",
            headers=auth_headers(token),
            json={"name": "Should Fail"},
        )
        assert response_patch.status_code == 403


# ============================================================================
# TEST SUITE 6: ORGANIZATION MEMBER CRUD
# ============================================================================


class TestOrganizationMemberCRUD:
    """Test organization member management operations"""

    def test_list_org_members(self, client, mock_jwks, seed_test_data):
        """Should list all members of an organization"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            role="owner",
        )

        response = client.get(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/members", headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["members"]) == 3

    def test_filter_members_by_role(self, client, mock_jwks, seed_test_data):
        """Should filter members by role"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            role="owner",
        )

        response = client.get(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/members?role=admin",
            headers=auth_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["members"][0]["role"] == "admin"

    def test_admin_can_update_member_role(self, client, mock_jwks, seed_test_data):
        """Admin should be able to update member roles"""
        token = create_test_token(
            user_id=TEST_ADMIN_ID,
            auth0_id="auth0|admin",
            email="admin@example.com",
            org_id=TEST_ORG_1_ID,
            role="admin",
        )

        response = client.patch(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/members/{TEST_USER_2_ID}",
            headers=auth_headers(token),
            json={"role": "admin"},
        )

        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    def test_member_cannot_update_roles(self, client, mock_jwks, seed_test_data):
        """Member should not be able to update roles"""
        token = create_test_token(
            user_id=TEST_USER_2_ID,
            auth0_id="auth0|user2",
            email="user2@example.com",
            org_id=TEST_ORG_1_ID,
            role="member",
        )

        response = client.patch(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/members/{TEST_USER_2_ID}",
            headers=auth_headers(token),
            json={"role": "admin"},
        )

        assert response.status_code == 403

    def test_admin_can_remove_member(self, client, mock_jwks, seed_test_data):
        """Admin should be able to remove members"""
        token = create_test_token(
            user_id=TEST_ADMIN_ID,
            auth0_id="auth0|admin",
            email="admin@example.com",
            org_id=TEST_ORG_1_ID,
            role="admin",
        )

        response = client.delete(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/members/{TEST_USER_2_ID}",
            headers=auth_headers(token),
        )

        assert response.status_code == 204

    def test_cannot_remove_last_owner(self, client, mock_jwks, seed_test_data):
        """Should not be able to remove the last owner"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            role="owner",
        )

        response = client.delete(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/members/{TEST_USER_1_ID}",
            headers=auth_headers(token),
        )

        # May return 400 or 403 depending on implementation
        assert response.status_code in [400, 403]


# ============================================================================
# TEST SUITE 7: API KEY AUTHENTICATION
# ============================================================================


class TestAPIKeyAuthentication:
    """Test API key creation, listing, and revocation"""

    def test_admin_can_create_api_key(self, client, mock_jwks, seed_test_data):
        """Admin should be able to create API keys"""
        token = create_test_token(
            user_id=TEST_ADMIN_ID,
            auth0_id="auth0|admin",
            email="admin@example.com",
            org_id=TEST_ORG_1_ID,
            role="admin",
        )

        response = client.post(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/api-keys",
            headers=auth_headers(token),
            json={
                "name": "Test API Key",
                "description": "For testing",
                "scopes": ["read:documents", "write:documents"],
                "rate_limit": 100,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "api_key" in data
        assert data["api_key"].startswith("cogent_pk_")
        assert "key_id" in data

    def test_member_cannot_create_api_key(self, client, mock_jwks, seed_test_data):
        """Member should not be able to create API keys"""
        token = create_test_token(
            user_id=TEST_USER_2_ID,
            auth0_id="auth0|user2",
            email="user2@example.com",
            org_id=TEST_ORG_1_ID,
            role="member",
        )

        response = client.post(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/api-keys",
            headers=auth_headers(token),
            json={"name": "Should Fail"},
        )

        assert response.status_code == 403

    def test_list_api_keys(self, client, mock_jwks, seed_test_data):
        """Should list organization's API keys"""
        # First create an API key
        admin_token = create_test_token(
            user_id=TEST_ADMIN_ID,
            auth0_id="auth0|admin",
            email="admin@example.com",
            org_id=TEST_ORG_1_ID,
            role="admin",
        )

        create_response = client.post(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/api-keys",
            headers=auth_headers(admin_token),
            json={"name": "Test Key", "scopes": ["read:documents"]},
        )
        assert create_response.status_code == 201

        # List API keys
        list_response = client.get(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/api-keys", headers=auth_headers(admin_token)
        )

        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data) >= 1
        assert data[0]["name"] == "Test Key"

    def test_revoke_api_key(self, client, mock_jwks, seed_test_data):
        """Should be able to revoke API keys"""
        admin_token = create_test_token(
            user_id=TEST_ADMIN_ID,
            auth0_id="auth0|admin",
            email="admin@example.com",
            org_id=TEST_ORG_1_ID,
            role="admin",
        )

        # Create key
        create_response = client.post(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/api-keys",
            headers=auth_headers(admin_token),
            json={"name": "Key to Revoke"},
        )
        key_id = create_response.json()["key_id"]

        # Revoke key
        revoke_response = client.delete(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/api-keys/{key_id}",
            headers=auth_headers(admin_token),
        )

        assert revoke_response.status_code == 204

    def test_cannot_create_more_than_max_keys(self, client, mock_jwks, seed_test_data):
        """Should enforce maximum API key limit"""
        admin_token = create_test_token(
            user_id=TEST_ADMIN_ID,
            auth0_id="auth0|admin",
            email="admin@example.com",
            org_id=TEST_ORG_1_ID,
            role="admin",
        )

        # Mock the count to return max limit
        with patch(
            "backend.repositories.api_key.APIKeyRepository.count_active_by_org"
        ) as mock_count:
            mock_count.return_value = 50  # Max limit

            response = client.post(
                f"/api/v1/orgs/{TEST_ORG_1_ID}/api-keys",
                headers=auth_headers(admin_token),
                json={"name": "Should Fail"},
            )

            assert response.status_code == 429
            # Just verify 429 status, message format can vary


# ============================================================================
# TEST SUITE 8: RATE LIMITING
# ============================================================================


class TestRateLimiting:
    """Test rate limiting behavior for authenticated and unauthenticated requests"""

    @pytest.mark.skip(reason="Rate limiting requires Redis and slowapi configuration")
    def test_authenticated_higher_rate_limit(
        self, client, mock_jwks, mock_redis, seed_test_data
    ):
        """Authenticated users should have higher rate limits"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            role="member",
        )

        # Make multiple requests
        for i in range(25):  # More than public limit (20)
            response = client.get("/api/v1/auth/me", headers=auth_headers(token))
            if i < 24:
                assert response.status_code == 200

        # Should still work (authenticated limit is 100)
        assert response.status_code == 200

    @pytest.mark.skip(reason="Rate limiting requires Redis configuration")
    def test_unauthenticated_lower_rate_limit(self, client, mock_redis):
        """Unauthenticated requests should have lower rate limits"""
        # Make requests to public endpoint
        for i in range(21):  # More than public limit
            response = client.get("/api/v1/health")

        # Last request should be rate limited
        assert response.status_code == 429


# ============================================================================
# TEST SUITE 9: WEBHOOK SIGNATURE VERIFICATION
# ============================================================================


class TestWebhookSignatureVerification:
    """Test Auth0 webhook signature verification"""

    def test_valid_webhook_signature(self, client):
        """Valid webhook signature should be accepted"""
        secret = "test_webhook_secret"
        payload = {"event": "post-registration", "user_id": "auth0|123"}
        body = json.dumps(payload).encode("utf-8")

        signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        with patch("backend.webhooks.auth0.settings") as mock_settings:
            mock_settings.auth0_webhook_secret = secret

            response = client.post(
                "/webhooks/auth0/events",
                headers={"X-Auth0-Signature": f"sha256={signature}"},
                json=payload,
            )

            # Note: May return 202 or other status depending on implementation
            assert response.status_code != 401

    def test_invalid_webhook_signature(self, client):
        """Invalid webhook signature should be rejected"""
        with patch("backend.webhooks.auth0.settings") as mock_settings:
            mock_settings.auth0_webhook_secret = "test_secret"

            response = client.post(
                "/webhooks/auth0/events",
                headers={"X-Auth0-Signature": "sha256=invalid_signature"},
                json={"event": "test"},
            )

            assert response.status_code == 401

    def test_missing_webhook_signature(self, client):
        """Missing webhook signature should be rejected"""
        response = client.post("/webhooks/auth0/events", json={"event": "test"})

        assert response.status_code == 401


# ============================================================================
# TEST SUITE 10: FEATURE FLAGS WITH AUTH CONTEXT
# ============================================================================


class TestFeatureFlagsWithAuth:
    """Test feature flags respect auth context (role, plan)"""

    def test_feature_flags_for_free_plan(self, client, mock_jwks, seed_test_data):
        """Free plan should have limited features"""
        token = create_test_token(
            user_id=TEST_USER_2_ID,
            auth0_id="auth0|user2",
            email="user2@example.com",
            org_id=TEST_ORG_1_ID,
            role="member",
            plan="free",
        )

        response = client.get("/api/v1/features", headers=auth_headers(token))

        assert response.status_code == 200
        data = response.json()
        # Free plan should have basic features only
        assert "features" in data

    def test_feature_flags_for_pro_plan(self, client, mock_jwks, seed_test_data):
        """Pro plan should have more features"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            role="owner",
            plan="pro",
        )

        response = client.get("/api/v1/features", headers=auth_headers(token))

        assert response.status_code == 200
        data = response.json()
        assert "features" in data

    def test_check_specific_feature_flag(self, client, mock_jwks, seed_test_data):
        """Should be able to check specific feature"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            role="owner",
            plan="enterprise",
        )

        response = client.get(
            "/api/v1/features/advanced_analytics", headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data


# ============================================================================
# TEST SUITE 11: ERROR SCENARIOS
# ============================================================================


class TestErrorScenarios:
    """Test comprehensive error handling"""

    def test_unauthorized_error_format(self, client):
        """401 errors should have consistent format"""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"] == "Unauthorized"
        assert "message" in data

    def test_forbidden_error_format(self, client, mock_jwks, seed_test_data):
        """403 errors should have consistent format"""
        token = create_test_token(
            user_id=TEST_USER_2_ID,
            auth0_id="auth0|user2",
            email="user2@example.com",
            org_id=TEST_ORG_1_ID,
            role="member",
        )

        response = client.patch(
            f"/api/v1/orgs/{TEST_ORG_1_ID}",
            headers=auth_headers(token),
            json={"name": "Should Fail"},
        )

        assert response.status_code == 403
        data = response.json()
        # Accept either detail or message field
        assert "detail" in data or "message" in data

    def test_not_found_error_format(self, client, mock_jwks, seed_test_data):
        """404 errors should have consistent format"""
        token = create_test_token(
            user_id=TEST_USER_1_ID,
            auth0_id="auth0|user1",
            email="user1@example.com",
            org_id=TEST_ORG_1_ID,
            role="owner",
        )

        fake_org_id = uuid4()
        response = client.get(
            f"/api/v1/orgs/{fake_org_id}", headers=auth_headers(token)
        )

        assert response.status_code in [403, 404]

    def test_validation_error_format(self, client, mock_jwks, seed_test_data):
        """422 validation errors should have consistent format"""
        token = create_test_token(
            user_id=TEST_ADMIN_ID,
            auth0_id="auth0|admin",
            email="admin@example.com",
            org_id=TEST_ORG_1_ID,
            role="admin",
        )

        response = client.post(
            f"/api/v1/orgs/{TEST_ORG_1_ID}/api-keys",
            headers=auth_headers(token),
            json={"name": ""},  # Invalid: empty name
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
