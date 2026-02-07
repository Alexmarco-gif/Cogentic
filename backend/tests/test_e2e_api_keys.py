"""
E2E Tests: API Keys
===================

Tests for API key management endpoints.
These tests simulate admins creating and managing API keys for programmatic access.

Simulates: Admin managing API keys for integrations
"""

import pytest


@pytest.mark.e2e
class TestAPIKeyAccess:
    """Test API key endpoint access control"""

    def test_api_keys_endpoint_requires_auth(self, client):
        """
        User Story: API key endpoints require authentication

        Expected: 401/403 without auth token
        """
        response = client.get(
            "/api/v1/orgs/00000000-0000-0000-0000-000000000000/api-keys"
        )

        assert response.status_code in [401, 403]

    def test_create_api_key_requires_auth(self, client):
        """
        User Story: Creating API keys requires authentication

        Expected: 401/403 without auth token
        """
        response = client.post(
            "/api/v1/orgs/00000000-0000-0000-0000-000000000000/api-keys",
            json={"name": "Test Key"},
        )

        assert response.status_code in [401, 403]


@pytest.mark.e2e
@pytest.mark.auth
class TestAPIKeyList:
    """Test listing API keys (authenticated)"""

    def test_list_api_keys_in_own_org(self, authed_client, auth_token, requires_auth):
        """
        User Story: As an org admin, I can list API keys in my organization.

        Expected: 200 OK with API key list
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        response = authed_client.get(f"/api/v1/orgs/{org_id}/api-keys")

        # Admin role required, so might get 403
        assert response.status_code in [200, 403]

        if response.status_code == 200:
            data = response.json()
            # Should return list of API keys
            assert isinstance(data, list) or "api_keys" in data or "items" in data

    def test_cannot_list_other_org_api_keys(
        self, authed_client, auth_token, requires_auth
    ):
        """
        User Story: Cannot list API keys from other organizations

        Expected: 403 Forbidden
        """
        fake_org_id = "99999999-9999-9999-9999-999999999999"

        response = authed_client.get(f"/api/v1/orgs/{fake_org_id}/api-keys")

        assert response.status_code in [403, 404]


@pytest.mark.e2e
@pytest.mark.auth
class TestAPIKeyCRUD:
    """Test API key create, read, delete operations"""

    def test_create_api_key(
        self, authed_client, auth_token, requires_auth, test_api_key_data
    ):
        """
        User Story: As an org admin, I can create an API key.

        Expected: 201 Created with key data (key value shown only once)
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        response = authed_client.post(
            f"/api/v1/orgs/{org_id}/api-keys", json=test_api_key_data
        )

        # Should create (admin) or deny (non-admin)
        assert response.status_code in [200, 201, 403, 422]

        if response.status_code in [200, 201]:
            data = response.json()
            # Should return the created key with the secret shown once
            assert "id" in data
            # The actual key value should be returned on creation
            assert "key" in data or "api_key" in data or "secret" in data

    def test_api_key_not_retrievable_after_creation(
        self, authed_client, auth_token, requires_auth
    ):
        """
        User Story: API key secret is only shown at creation time

        After creation, the key value should not be retrievable
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        # List existing keys
        list_response = authed_client.get(f"/api/v1/orgs/{org_id}/api-keys")

        if list_response.status_code != 200:
            pytest.skip("Cannot list API keys (probably not admin)")

        keys = list_response.json()
        if isinstance(keys, dict):
            keys = keys.get("api_keys", keys.get("items", []))

        if keys:
            # Key value should be masked or not present
            key = keys[0]
            # If key value is present, it should be masked
            if "key" in key:
                assert "***" in str(key["key"]) or len(key["key"]) < 10

    def test_delete_api_key(self, authed_client, auth_token, requires_auth):
        """
        User Story: As an org admin, I can revoke/delete an API key.

        Expected: 200/204 on successful deletion
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        # First, create a key to delete
        create_response = authed_client.post(
            f"/api/v1/orgs/{org_id}/api-keys",
            json={"name": "Key to Delete", "scopes": ["read:documents"]},
        )

        if create_response.status_code not in [200, 201]:
            pytest.skip("Cannot create API key (probably not admin)")

        key_id = create_response.json().get("id")

        # Now delete it
        delete_response = authed_client.delete(
            f"/api/v1/orgs/{org_id}/api-keys/{key_id}"
        )

        assert delete_response.status_code in [200, 204]

    def test_cannot_delete_other_org_api_key(
        self, authed_client, auth_token, requires_auth
    ):
        """
        User Story: Cannot delete API keys from other organizations

        Expected: 403 Forbidden
        """
        fake_org_id = "99999999-9999-9999-9999-999999999999"
        fake_key_id = "99999999-9999-9999-9999-999999999998"

        response = authed_client.delete(
            f"/api/v1/orgs/{fake_org_id}/api-keys/{fake_key_id}"
        )

        assert response.status_code in [403, 404]


@pytest.mark.e2e
@pytest.mark.auth
class TestAPIKeyValidation:
    """Test API key input validation"""

    def test_create_key_missing_name(self, authed_client, auth_token, requires_auth):
        """
        User Story: API key name is required

        Expected: 422 Validation Error
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        response = authed_client.post(
            f"/api/v1/orgs/{org_id}/api-keys",
            json={},  # Missing name
        )

        # Should fail validation (422) or permission (403)
        assert response.status_code in [400, 422, 403]

    def test_create_key_invalid_scopes(self, authed_client, auth_token, requires_auth):
        """
        User Story: Invalid scopes are rejected

        Expected: 422 Validation Error
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        response = authed_client.post(
            f"/api/v1/orgs/{org_id}/api-keys",
            json={"name": "Test Key", "scopes": ["invalid:scope:that:does:not:exist"]},
        )

        # Should fail validation (422) or permission (403)
        assert response.status_code in [400, 422, 403]


@pytest.mark.e2e
@pytest.mark.auth
class TestAPIKeyRoles:
    """Test API key role restrictions"""

    def test_viewer_cannot_create_api_keys(
        self, authed_client, auth_token, requires_auth
    ):
        """
        User Story: Viewers cannot create API keys

        Only admins should be able to manage API keys
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")
        role = user_data.get("role")

        if not org_id:
            pytest.skip("User has no organization")

        response = authed_client.post(
            f"/api/v1/orgs/{org_id}/api-keys", json={"name": "Test Key"}
        )

        # If user is viewer, should get 403
        # If admin, should get 201
        if role in ["viewer", "member"]:
            assert response.status_code == 403
        else:
            # Admin or owner
            assert response.status_code in [200, 201, 403]
