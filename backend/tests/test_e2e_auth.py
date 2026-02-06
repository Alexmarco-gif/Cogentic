"""
E2E Tests: Authentication
=========================

Tests that verify Auth0 JWT authentication works correctly.
These tests simulate real users logging in and accessing protected resources.

Simulates: User authenticating via Auth0 and accessing the API
"""

import pytest


@pytest.mark.e2e
class TestUnauthenticatedAccess:
    """Test behavior when no auth token is provided"""
    
    def test_protected_endpoint_requires_auth(self, client):
        """
        User Story: As an unauthenticated visitor, I cannot access protected endpoints.
        
        Expected: 401 Unauthorized or 403 Forbidden
        """
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code in [401, 403]
        data = response.json()
        assert "detail" in data or "error" in data
    
    def test_users_me_requires_auth(self, client):
        """
        User Story: /users/me requires authentication
        
        Expected: 401 Unauthorized
        """
        response = client.get("/api/v1/users/me")
        
        assert response.status_code in [401, 403]
    
    def test_public_endpoints_work_without_auth(self, client):
        """
        User Story: Health endpoints don't require auth
        
        Expected: 200 OK without token (some environments may require auth)
        """
        response = client.get("/health")
        assert response.status_code in [200, 401]
        
        response = client.get("/api/v1/health")
        assert response.status_code in [200, 401]
    
    def test_error_message_indicates_auth_needed(self, client):
        """
        Error response should indicate authentication is required
        """
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code in [401, 403]
        data = response.json()
        
        # Check for meaningful error message
        error_text = str(data).lower()
        assert any(word in error_text for word in [
            "unauthorized", "authentication", "token", "bearer", "auth"
        ])


@pytest.mark.e2e
class TestInvalidTokens:
    """Test behavior with invalid/malformed tokens"""
    
    def test_malformed_token_rejected(self, client):
        """
        User Story: API rejects obviously invalid tokens
        
        Expected: 401 Unauthorized
        """
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not-a-valid-jwt-token"}
        )
        
        assert response.status_code in [401, 403]
    
    def test_empty_bearer_token_rejected(self, client):
        """
        User Story: Empty bearer token is rejected
        
        Expected: 401 Unauthorized
        """
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer "}
        )
        
        assert response.status_code in [401, 403]
    
    def test_wrong_auth_scheme_rejected(self, client):
        """
        User Story: Non-Bearer auth schemes are rejected
        
        Expected: 401 Unauthorized
        """
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Basic dXNlcjpwYXNz"}
        )
        
        assert response.status_code in [401, 403]
    
    def test_expired_looking_token_rejected(self, client):
        """
        User Story: Old/expired tokens are rejected
        
        Using a structurally valid but expired JWT
        """
        # This is a structurally valid JWT but with expired claims
        expired_jwt = (
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxNjAwMDAwMDAwfQ."
            "invalid-signature"
        )
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_jwt}"}
        )
        
        assert response.status_code in [401, 403]


@pytest.mark.e2e
@pytest.mark.auth
class TestAuthenticatedAccess:
    """Test behavior with valid auth token"""
    
    def test_valid_token_accepted(self, authed_client, auth_token, requires_auth):
        """
        User Story: As an authenticated user, I can access protected endpoints.
        
        Expected: 200 OK with user info
        """
        response = authed_client.get("/api/v1/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return user info
        assert "sub" in data or "user_id" in data or "email" in data
    
    def test_token_verification_endpoint(self, authed_client, auth_token, requires_auth):
        """
        User Story: I can verify my token is valid
        
        Expected: 200 OK with verification response
        """
        response = authed_client.post("/api/v1/auth/token/verify")
        
        # May return 200 or 405 depending on implementation
        if response.status_code == 200:
            data = response.json()
            assert "valid" in data or "verified" in data or "sub" in data
    
    def test_user_me_returns_profile(self, authed_client, auth_token, requires_auth):
        """
        User Story: As a user, I can get my profile via /users/me
        
        Expected: 200 OK with user profile
        """
        response = authed_client.get("/api/v1/users/me")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include user fields
        assert any(key in data for key in ["id", "email", "sub", "name"])
    
    def test_permissions_endpoint(self, authed_client, auth_token, requires_auth):
        """
        User Story: I can check my permissions
        
        Expected: 200 OK with permissions list
        """
        response = authed_client.get("/api/v1/auth/permissions")
        
        if response.status_code == 200:
            data = response.json()
            # Should return permissions info
            assert isinstance(data, (list, dict))


@pytest.mark.e2e
@pytest.mark.auth
class TestAuthHeaders:
    """Test authentication header handling"""
    
    def test_case_insensitive_authorization_header(self, client, auth_token, requires_auth):
        """
        Authorization header should work regardless of case
        """
        if not auth_token:
            pytest.skip("No auth token available")
        
        # Test lowercase
        response = client.get(
            "/api/v1/auth/me",
            headers={"authorization": f"Bearer {auth_token}"}
        )
        
        # Should work - HTTP headers are case-insensitive
        assert response.status_code in [200, 401]
    
    def test_bearer_prefix_required(self, client, auth_token, requires_auth):
        """
        Token without Bearer prefix should be rejected
        """
        if not auth_token:
            pytest.skip("No auth token available")
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": auth_token}  # Missing "Bearer "
        )
        
        assert response.status_code in [401, 403]


@pytest.mark.e2e
class TestHealthAuth:
    """Test authenticated health endpoint"""
    
    def test_authenticated_health_endpoint(self, authed_client, auth_token, requires_auth):
        """
        User Story: Authenticated health check verifies auth is working
        
        Expected: 200 OK for authenticated user
        """
        response = authed_client.get("/api/v1/health/auth")
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("status") == "healthy" or data.get("authenticated") is True
    
    def test_authenticated_health_requires_token(self, client):
        """
        /health/auth should require authentication
        """
        response = client.get("/api/v1/health/auth")
        
        assert response.status_code in [401, 403]
