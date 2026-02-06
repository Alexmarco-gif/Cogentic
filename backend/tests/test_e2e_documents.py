"""
E2E Tests: Documents
====================

Tests for document management CRUD operations.
These tests simulate users uploading, viewing, and managing documents.

Simulates: User managing documents in their organization
"""

import pytest


@pytest.mark.e2e
class TestDocumentAccess:
    """Test document endpoint access control"""
    
    def test_documents_endpoint_requires_auth(self, client):
        """
        User Story: Document endpoints require authentication
        
        Expected: 401/403 without auth token
        """
        response = client.get(
            "/api/v1/orgs/00000000-0000-0000-0000-000000000000/documents"
        )
        
        assert response.status_code in [401, 403]
    
    def test_single_document_requires_auth(self, client):
        """
        User Story: Individual document access requires authentication
        
        Expected: 401/403 without auth token
        """
        response = client.get(
            "/api/v1/orgs/00000000-0000-0000-0000-000000000000/documents/00000000-0000-0000-0000-000000000001"
        )
        
        assert response.status_code in [401, 403]


@pytest.mark.e2e
@pytest.mark.auth
class TestDocumentList:
    """Test listing documents (authenticated)"""
    
    def test_list_documents_in_own_org(self, authed_client, auth_token, requires_auth):
        """
        User Story: As an org member, I can list documents in my organization.
        
        Expected: 200 OK with document list
        """
        # Get user's org_id first
        me_response = authed_client.get("/api/v1/users/me")
        
        if me_response.status_code != 200:
            pytest.skip("Could not get user info")
        
        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")
        
        if not org_id:
            pytest.skip("User has no organization")
        
        response = authed_client.get(f"/api/v1/orgs/{org_id}/documents")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return list of documents
        assert isinstance(data, list) or "documents" in data or "items" in data
    
    def test_cannot_list_other_org_documents(self, authed_client, auth_token, requires_auth):
        """
        User Story: Cannot list documents from other organizations
        
        Expected: 403 Forbidden
        """
        fake_org_id = "99999999-9999-9999-9999-999999999999"
        
        response = authed_client.get(f"/api/v1/orgs/{fake_org_id}/documents")
        
        assert response.status_code in [403, 404]
    
    def test_list_documents_pagination(self, authed_client, auth_token, requires_auth):
        """
        User Story: Document list supports pagination
        
        Expected: Pagination parameters work
        """
        me_response = authed_client.get("/api/v1/users/me")
        
        if me_response.status_code != 200:
            pytest.skip("Could not get user info")
        
        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")
        
        if not org_id:
            pytest.skip("User has no organization")
        
        # Test with limit parameter
        response = authed_client.get(
            f"/api/v1/orgs/{org_id}/documents",
            params={"limit": 5, "offset": 0}
        )
        
        assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.auth
class TestDocumentCRUD:
    """Test document create, read, update, delete operations"""
    
    def test_create_document(self, authed_client, auth_token, requires_auth, test_document_data):
        """
        User Story: As an org member, I can create/upload a document.
        
        Expected: 201 Created with document data
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
            json=test_document_data
        )
        
        # Should create or indicate permission issue
        assert response.status_code in [200, 201, 403, 422]
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            # Store for cleanup
            return data.get("id")
    
    def test_get_single_document(self, authed_client, auth_token, requires_auth):
        """
        User Story: As an org member, I can view a specific document.
        
        Note: Requires an existing document in the org
        """
        me_response = authed_client.get("/api/v1/users/me")
        
        if me_response.status_code != 200:
            pytest.skip("Could not get user info")
        
        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")
        
        if not org_id:
            pytest.skip("User has no organization")
        
        # First list documents to find one
        list_response = authed_client.get(f"/api/v1/orgs/{org_id}/documents")
        
        if list_response.status_code != 200:
            pytest.skip("Could not list documents")
        
        docs = list_response.json()
        if isinstance(docs, dict):
            docs = docs.get("documents", docs.get("items", []))
        
        if not docs:
            pytest.skip("No documents in organization")
        
        doc_id = docs[0].get("id")
        
        # Get single document
        response = authed_client.get(f"/api/v1/orgs/{org_id}/documents/{doc_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("id") == doc_id
    
    def test_cannot_access_other_org_document(self, authed_client, auth_token, requires_auth):
        """
        User Story: Cannot access documents in other organizations
        
        Expected: 403 Forbidden
        """
        fake_org_id = "99999999-9999-9999-9999-999999999999"
        fake_doc_id = "99999999-9999-9999-9999-999999999998"
        
        response = authed_client.get(
            f"/api/v1/orgs/{fake_org_id}/documents/{fake_doc_id}"
        )
        
        assert response.status_code in [403, 404]


@pytest.mark.e2e
@pytest.mark.auth
class TestDocumentValidation:
    """Test document input validation"""
    
    def test_invalid_org_id_format(self, authed_client, auth_token, requires_auth):
        """
        User Story: Invalid org ID format returns validation error
        
        Expected: 400/422 Validation Error
        """
        response = authed_client.get("/api/v1/orgs/invalid-uuid/documents")
        
        assert response.status_code in [400, 422, 404]
    
    def test_invalid_document_id_format(self, authed_client, auth_token, requires_auth):
        """
        User Story: Invalid document ID format returns validation error
        """
        me_response = authed_client.get("/api/v1/users/me")
        
        if me_response.status_code != 200:
            pytest.skip("Could not get user info")
        
        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")
        
        if not org_id:
            pytest.skip("User has no organization")
        
        response = authed_client.get(
            f"/api/v1/orgs/{org_id}/documents/not-a-valid-uuid"
        )
        
        assert response.status_code in [400, 422, 404]
    
    def test_create_document_missing_required_fields(self, authed_client, auth_token, requires_auth):
        """
        User Story: Creating document without required fields fails
        
        Expected: 422 Validation Error
        """
        me_response = authed_client.get("/api/v1/users/me")
        
        if me_response.status_code != 200:
            pytest.skip("Could not get user info")
        
        user_data = me_response.json()
        org_id = user_data.get("org_id") or user_data.get("organization_id")
        
        if not org_id:
            pytest.skip("User has no organization")
        
        # Empty body - missing required fields
        response = authed_client.post(
            f"/api/v1/orgs/{org_id}/documents",
            json={}
        )
        
        # Should fail validation
        assert response.status_code in [400, 422, 403]


@pytest.mark.e2e
@pytest.mark.auth
class TestDocumentFiltering:
    """Test document list filtering and search"""
    
    def test_filter_by_status(self, authed_client, auth_token, requires_auth):
        """
        User Story: I can filter documents by processing status
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
            params={"status": "completed"}
        )
        
        # Should accept filter parameter
        assert response.status_code == 200
    
    def test_search_documents(self, authed_client, auth_token, requires_auth):
        """
        User Story: I can search documents by filename
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
            params={"search": "test"}
        )
        
        # Should accept search parameter
        assert response.status_code == 200
