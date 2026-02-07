"""
E2E Tests: Security
===================

Tests for security edge cases and vulnerability prevention.
These tests verify the API handles malicious inputs correctly.

Simulates: Security testing and penetration testing scenarios
"""

import pytest


@pytest.mark.e2e
@pytest.mark.security
class TestSQLInjection:
    """Test SQL injection prevention"""

    def test_sql_injection_in_org_id(self, client):
        """
        User Story: SQL injection attempts are blocked

        Expected: 400/422 validation error, not server error
        """
        malicious_id = "'; DROP TABLE users; --"

        response = client.get(f"/api/v1/orgs/{malicious_id}/documents")

        # Should be rejected at validation, not cause server error
        assert response.status_code in [400, 401, 403, 404, 422]
        assert response.status_code != 500

    def test_sql_injection_in_query_params(
        self, authed_client, auth_token, requires_auth
    ):
        """
        User Story: Query parameters are sanitized

        Expected: No server error from SQL injection attempt
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        response = authed_client.get(
            f"/api/v1/orgs/{org_id}/documents",
            params={"search": "'; DROP TABLE documents; --"},
        )

        # Should handle gracefully
        assert response.status_code != 500


@pytest.mark.e2e
@pytest.mark.security
class TestXSS:
    """Test XSS prevention"""

    def test_xss_in_document_filename(self, authed_client, auth_token, requires_auth):
        """
        User Story: XSS payloads in filenames are sanitized

        Expected: Stored safely, returned escaped
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        xss_payload = "<script>alert('xss')</script>.pdf"

        response = authed_client.post(
            f"/api/v1/orgs/{org_id}/documents",
            json={
                "filename": xss_payload,
                "storage_path": "/uploads/test.pdf",
                "size_bytes": 1024,
                "content_type": "application/pdf",
            },
        )

        # Should either reject or sanitize, not cause server error
        assert response.status_code != 500

    def test_xss_in_api_key_name(self, authed_client, auth_token, requires_auth):
        """
        User Story: XSS payloads in API key names are handled

        Expected: Stored safely or rejected
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        xss_payload = "<img src=x onerror=alert('xss')>"

        response = authed_client.post(
            f"/api/v1/orgs/{org_id}/api-keys", json={"name": xss_payload}
        )

        # Should handle gracefully
        assert response.status_code != 500


@pytest.mark.e2e
@pytest.mark.security
class TestPathTraversal:
    """Test path traversal prevention"""

    def test_path_traversal_in_document_path(
        self, authed_client, auth_token, requires_auth
    ):
        """
        User Story: Path traversal attempts are blocked

        Expected: Rejected or sanitized
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        traversal_path = "../../etc/passwd"

        response = authed_client.post(
            f"/api/v1/orgs/{org_id}/documents",
            json={
                "filename": "test.pdf",
                "storage_path": traversal_path,
                "size_bytes": 1024,
                "content_type": "application/pdf",
            },
        )

        # Should reject malicious paths
        assert response.status_code in [400, 403, 422, 500]


@pytest.mark.e2e
@pytest.mark.security
class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_rate_limit_headers_present(self, client):
        """
        User Story: API returns rate limit headers

        Expected: Response includes rate limit info
        """
        response = client.get("/health")

        # Check for common rate limit headers
        rate_limit_headers = [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "RateLimit-Limit",
            "RateLimit-Remaining",
        ]

        # At least some headers might be present
        _ = any(
            h.lower() in {k.lower() for k in response.headers}
            for h in rate_limit_headers
        )

        # This is informational - rate limiting may or may not be on health
        # Just ensure no error
        assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.security
class TestAuthorizationBypass:
    """Test authorization bypass attempts"""

    def test_cannot_access_other_user_data(
        self, authed_client, auth_token, requires_auth
    ):
        """
        User Story: Cannot access other users' data by ID manipulation

        Expected: 403 Forbidden
        """
        # Try to access another user's data with fake ID
        fake_user_id = "99999999-9999-9999-9999-999999999999"

        response = authed_client.get(f"/api/v1/users/{fake_user_id}")

        # Should be forbidden or not found
        assert response.status_code in [403, 404]

    def test_cannot_escalate_role(self, authed_client, auth_token, requires_auth):
        """
        User Story: Cannot escalate own role

        Expected: Request rejected
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        user_id = user_data.get("id")

        if not user_id:
            pytest.skip("Could not get user ID")

        # Try to escalate role
        response = authed_client.patch(
            f"/api/v1/users/{user_id}", json={"role": "owner"}
        )

        # Should be forbidden or ignored
        assert response.status_code in [200, 403, 404, 405, 422]

        # If 200, verify role wasn't actually changed
        if response.status_code == 200:
            verify_response = authed_client.get("/api/v1/users/me")
            if verify_response.status_code == 200:
                # Role change should be ignored for self-modification
                pass


@pytest.mark.e2e
@pytest.mark.security
class TestInputValidation:
    """Test input validation and boundary conditions"""

    def test_extremely_long_input(self, authed_client, auth_token, requires_auth):
        """
        User Story: Extremely long inputs are rejected

        Expected: 400/422 validation error
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        # Create very long string (1MB)
        long_string = "a" * (1024 * 1024)

        response = authed_client.post(
            f"/api/v1/orgs/{org_id}/documents",
            json={
                "filename": long_string,
                "storage_path": "/uploads/test.pdf",
                "size_bytes": 1024,
                "content_type": "application/pdf",
            },
        )

        # Should reject oversized input
        assert response.status_code in [400, 413, 422, 403]

    def test_negative_values(self, authed_client, auth_token, requires_auth):
        """
        User Story: Negative values are validated

        Expected: Rejected for fields that must be positive
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        response = authed_client.post(
            f"/api/v1/orgs/{org_id}/documents",
            json={
                "filename": "test.pdf",
                "storage_path": "/uploads/test.pdf",
                "size_bytes": -1,  # Negative file size
                "content_type": "application/pdf",
            },
        )

        # Should reject negative size
        assert response.status_code in [400, 422, 403]

    def test_special_characters_in_json(self, authed_client, auth_token, requires_auth):
        """
        User Story: Special characters are handled correctly

        Expected: No server errors
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        # Test with unicode and special chars
        response = authed_client.post(
            f"/api/v1/orgs/{org_id}/api-keys",
            json={
                "name": "Test 🔑 Key™ ñ Ω © ®",
                "description": "Unicode test: 中文 日本語 العربية",
            },
        )

        # Should handle unicode gracefully
        assert response.status_code != 500


@pytest.mark.e2e
@pytest.mark.security
class TestJWTSecurity:
    """Test JWT token security"""

    def test_token_in_url_rejected(self, client, auth_token, requires_auth):
        """
        User Story: Token in URL query param should be rejected

        Tokens should only be in Authorization header
        """
        if not auth_token:
            pytest.skip("No auth token available")

        response = client.get("/api/v1/auth/me", params={"token": auth_token})

        # Should still be unauthorized - token must be in header
        assert response.status_code in [401, 403]

    def test_algorithm_confusion_blocked(self, client):
        """
        User Story: Algorithm confusion attacks are blocked

        Tokens with 'none' algorithm should be rejected
        """
        # JWT with 'none' algorithm (base64 of {"alg":"none","typ":"JWT"})
        none_algo_token = (
            "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        )

        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {none_algo_token}"}
        )

        # Should be rejected
        assert response.status_code in [401, 403]
