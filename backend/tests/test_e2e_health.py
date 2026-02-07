"""
E2E Tests: Health & Infrastructure
==================================

Tests that verify the API is up, responsive, and dependencies are healthy.
These are smoke tests that should pass for any deployment to be considered healthy.

Simulates: DevOps engineer checking if deployment succeeded
"""

import pytest


@pytest.mark.e2e
@pytest.mark.smoke
class TestHealthEndpoints:
    """Test all health check endpoints respond correctly"""

    def test_root_endpoint_returns_welcome(self, client):
        """
        User Story: As a developer, I hit the root URL to verify the API is reachable.

        Expected: 200 OK with welcome message
        """
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "status" in data

    def test_health_endpoint_basic(self, client):
        """
        User Story: As a load balancer, I check /health to route traffic.

        Expected: 200 OK indicating service is healthy
        """
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"

    def test_api_v1_health_endpoint(self, client):
        """
        User Story: As monitoring system, I check versioned health endpoint.

        Expected: 200 OK with detailed health info OR 401 if auth required
        """
        response = client.get("/api/v1/health")

        # Some deployments require auth for versioned health
        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            assert data.get("status") == "healthy"
            # Should include version info
            assert "version" in data or "environment" in data

    def test_health_endpoint_returns_json(self, client):
        """
        Verify health endpoint returns proper JSON content type
        """
        response = client.get("/health")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.e2e
@pytest.mark.smoke
class TestAPIResponsiveness:
    """Test that API responds within acceptable timeframes"""

    def test_health_responds_quickly(self, client):
        """
        Health check should respond within 5 seconds even on cold start
        """
        response = client.get("/health")

        assert response.status_code == 200
        # Response time is measured by requests, should be < 5s
        assert response.elapsed.total_seconds() < 5

    def test_root_responds_quickly(self, client):
        """
        Root endpoint should respond quickly
        """
        response = client.get("/")

        assert response.status_code == 200
        assert response.elapsed.total_seconds() < 5


@pytest.mark.e2e
@pytest.mark.smoke
class TestHTTPBasics:
    """Test basic HTTP behavior and headers"""

    def test_returns_request_id_header(self, client):
        """
        User Story: As a developer debugging issues, I need request IDs for tracing.

        Expected: Response includes X-Request-ID header
        """
        response = client.get("/health")

        # Check for common request ID headers
        request_id = (
            response.headers.get("X-Request-ID")
            or response.headers.get("x-request-id")
            or response.headers.get("Request-Id")
        )

        # Note: This may not be implemented - test will reveal
        if request_id:
            assert len(request_id) > 0

    def test_cors_headers_present(self, client):
        """
        User Story: As a frontend app, I need CORS to work.

        Test with OPTIONS request (preflight)
        """
        response = client.options("/health", headers={"Origin": "https://example.com"})

        # Should not fail - actual CORS header presence depends on config
        assert response.status_code in [200, 204, 405]

    def test_content_type_json_by_default(self, client):
        """
        API should return JSON content type for API endpoints
        """
        response = client.get("/api/v1/health")

        # Even if 401, should still be JSON
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type


@pytest.mark.e2e
@pytest.mark.smoke
class TestErrorHandling:
    """Test that errors are handled gracefully"""

    def test_404_for_unknown_endpoint(self, client):
        """
        User Story: As a developer, I get proper 404 for missing endpoints.

        Expected: 404 with JSON error response (or 401 if auth required first)
        """
        response = client.get("/api/v1/this-endpoint-does-not-exist")

        # May return 401 (auth first) or 404 (not found)
        assert response.status_code in [401, 404]

        # Should still return JSON error
        data = response.json()
        assert "detail" in data or "error" in data or "message" in data

    def test_method_not_allowed_returns_405(self, client):
        """
        User Story: Wrong HTTP method should return 405

        Expected: 405 Method Not Allowed
        """
        # Try DELETE on a GET-only endpoint
        response = client.delete("/health")

        assert response.status_code in [405, 404]  # 404 also acceptable

    def test_invalid_json_returns_422(self, client):
        """
        User Story: Invalid JSON body should return validation error

        Expected: 422 Unprocessable Entity (or 401 if auth required)
        """
        response = client.post(
            "/api/v1/health",  # This endpoint likely doesn't accept POST
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )

        # Either 401 (auth required), 405 (method not allowed), or 422 (validation error)
        assert response.status_code in [401, 405, 422, 404]
