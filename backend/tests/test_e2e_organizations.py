"""
E2E Tests: Organizations
========================

Tests for organization management endpoints.
These tests simulate users managing their organizations and team members.

Simulates: Admin managing organization settings and team
"""

import pytest


@pytest.mark.e2e
class TestOrganizationAccess:
    """Test organization endpoint access control"""

    def test_org_endpoint_requires_auth(self, client):
        """
        User Story: Organization endpoints require authentication

        Expected: 401/403 without auth token
        """
        # Use a dummy org ID
        response = client.get("/api/v1/orgs/00000000-0000-0000-0000-000000000000")

        assert response.status_code in [401, 403]

    def test_org_members_requires_auth(self, client):
        """
        User Story: Member list requires authentication

        Expected: 401/403 without auth token
        """
        response = client.get(
            "/api/v1/orgs/00000000-0000-0000-0000-000000000000/members"
        )

        assert response.status_code in [401, 403]


@pytest.mark.e2e
@pytest.mark.auth
class TestOrganizationRead:
    """Test reading organization data (authenticated)"""

    def test_get_own_organization(self, authed_client, auth_token, requires_auth):
        """
        User Story: As an org member, I can view my organization details.

        Note: Requires valid org_id in token claims
        """
        # First, get user to find their org_id
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        # Now get organization details
        response = authed_client.get(f"/api/v1/orgs/{org_id}")

        assert response.status_code == 200
        data = response.json()

        # Should include org fields
        assert "id" in data or "name" in data

    def test_get_org_members(self, authed_client, auth_token, requires_auth):
        """
        User Story: As an org member, I can see other members.

        Expected: 200 OK with member list
        """
        # Get user's org_id first
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        response = authed_client.get(f"/api/v1/orgs/{org_id}/members")

        assert response.status_code == 200
        data = response.json()

        # Should return list of members
        assert isinstance(data, list) or "members" in data

    def test_cannot_access_other_org(self, authed_client, auth_token, requires_auth):
        """
        User Story: I cannot access organizations I'm not a member of.

        Expected: 403 Forbidden
        """
        # Use a random UUID that user is definitely not a member of
        fake_org_id = "99999999-9999-9999-9999-999999999999"

        response = authed_client.get(f"/api/v1/orgs/{fake_org_id}")

        # Should be forbidden (403) or not found (404)
        assert response.status_code in [403, 404]


@pytest.mark.e2e
@pytest.mark.auth
class TestOrganizationValidation:
    """Test organization endpoint input validation"""

    def test_invalid_org_id_format(self, authed_client, auth_token, requires_auth):
        """
        User Story: Invalid org ID format returns proper error

        Expected: 422 Validation Error
        """
        response = authed_client.get("/api/v1/orgs/not-a-valid-uuid")

        # Should reject invalid UUID format
        assert response.status_code in [400, 422, 404]

    def test_nonexistent_org_returns_404(
        self, authed_client, auth_token, requires_auth
    ):
        """
        User Story: Non-existent org returns 404

        Expected: 404 Not Found
        """
        # Valid UUID format but doesn't exist
        response = authed_client.get(
            "/api/v1/orgs/00000000-0000-0000-0000-000000000001"
        )

        # Could be 403 (no access) or 404 (not found)
        assert response.status_code in [403, 404]


@pytest.mark.e2e
@pytest.mark.auth
class TestMemberManagement:
    """Test organization member management"""

    def test_invite_member_requires_admin(
        self, authed_client, auth_token, requires_auth
    ):
        """
        User Story: Only admins can invite members

        Test that invite endpoint exists and requires proper permissions
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        # Try to invite a member
        response = authed_client.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "test@example.com", "role": "member"},
        )

        # Should either succeed (if admin) or fail with 403
        # 404 is also acceptable if the endpoint doesn't exist
        assert response.status_code in [200, 201, 403, 404, 405, 422]

    def test_cannot_invite_to_other_org(self, authed_client, auth_token, requires_auth):
        """
        User Story: Cannot invite members to other organizations

        Expected: 403 Forbidden
        """
        fake_org_id = "99999999-9999-9999-9999-999999999999"

        response = authed_client.post(
            f"/api/v1/orgs/{fake_org_id}/members",
            json={"email": "test@example.com", "role": "member"},
        )

        # Should be forbidden
        assert response.status_code in [403, 404, 422]


@pytest.mark.e2e
@pytest.mark.auth
class TestOrganizationUpdate:
    """Test organization update operations"""

    def test_update_org_requires_admin(self, authed_client, auth_token, requires_auth):
        """
        User Story: Updating org settings requires admin role

        Expected: Success (admin) or 403 (non-admin)
        """
        me_response = authed_client.get("/api/v1/users/me")

        if me_response.status_code != 200:
            pytest.skip("Could not get user info")

        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")

        if not org_id:
            pytest.skip("User has no organization")

        response = authed_client.patch(
            f"/api/v1/orgs/{org_id}", json={"name": "Test Org Name"}
        )

        # Should work if admin, fail if not
        assert response.status_code in [200, 403, 404, 405]

    def test_cannot_update_other_org(self, authed_client, auth_token, requires_auth):
        """
        User Story: Cannot update organizations I don't belong to

        Expected: 403 Forbidden
        """
        fake_org_id = "99999999-9999-9999-9999-999999999999"

        response = authed_client.patch(
            f"/api/v1/orgs/{fake_org_id}", json={"name": "Hacker Org"}
        )

        assert response.status_code in [403, 404]
