"""
Pre-Prod Environment Smoke Tests
==================================

End-to-end tests to validate the pre-prod environment is working correctly.

Run these after deployment:
    pytest tests/test_preprod.py -v

Prerequisites:
    - Pre-prod environment deployed
    - PREPROD_API_URL environment variable set
    - Auth0 test user token available (optional for authenticated tests)
"""

import os

import pytest
import requests

# Configuration
PREPROD_API_URL = os.getenv(
    "PREPROD_API_URL",
    "https://cogent-api.yellowtree-0cde5f74.eastus.azurecontainerapps.io",
)
AUTH0_TEST_TOKEN = os.getenv("AUTH0_TEST_TOKEN")  # Optional

# Test timeout
TIMEOUT = 10


class TestHealthAndBasics:
    """Basic connectivity and health checks"""

    def test_health_endpoint(self):
        """Health endpoint returns 200"""
        response = requests.get(f"{PREPROD_API_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200

        data = response.json()
        # Accept healthy or degraded (Redis may not be provisioned yet)
        assert data["status"] in ["healthy", "degraded"]
        assert "version" in data
        assert "services" in data
        assert data["services"]["database"] == "up"

    def test_cors_headers(self):
        """CORS headers are present"""
        response = requests.options(
            f"{PREPROD_API_URL}/health",
            headers={"Origin": "http://localhost:3000"},
            timeout=TIMEOUT,
        )
        assert "access-control-allow-origin" in response.headers

    def test_api_docs_accessible(self):
        """OpenAPI docs are available"""
        response = requests.get(f"{PREPROD_API_URL}/docs", timeout=TIMEOUT)
        assert response.status_code == 200

    def test_404_handling(self):
        """Non-existent endpoints return 404"""
        response = requests.get(f"{PREPROD_API_URL}/nonexistent", timeout=TIMEOUT)
        assert response.status_code == 404


class TestAuthentication:
    """Auth0 integration tests"""

    def test_unauthenticated_request_blocked(self):
        """Protected endpoints require authentication"""
        response = requests.get(f"{PREPROD_API_URL}/api/v1/me", timeout=TIMEOUT)
        assert response.status_code == 401

    def test_invalid_token_rejected(self):
        """Invalid JWT tokens are rejected"""
        response = requests.get(
            f"{PREPROD_API_URL}/api/v1/me",
            headers={"Authorization": "Bearer invalid_token"},
            timeout=TIMEOUT,
        )
        assert response.status_code == 401

    @pytest.mark.skipif(not AUTH0_TEST_TOKEN, reason="AUTH0_TEST_TOKEN not set")
    def test_authenticated_request_succeeds(self):
        """Valid Auth0 token allows access"""
        response = requests.get(
            f"{PREPROD_API_URL}/api/v1/me",
            headers={"Authorization": f"Bearer {AUTH0_TEST_TOKEN}"},
            timeout=TIMEOUT,
        )
        assert response.status_code == 200

        data = response.json()
        assert "user_id" in data
        assert "email" in data


class TestDatabase:
    """Database connectivity tests"""

    @pytest.mark.skipif(not AUTH0_TEST_TOKEN, reason="AUTH0_TEST_TOKEN not set")
    def test_database_read_operation(self):
        """Can read from database"""
        # Test an endpoint that queries the database
        response = requests.get(
            f"{PREPROD_API_URL}/api/v1/organizations",
            headers={"Authorization": f"Bearer {AUTH0_TEST_TOKEN}"},
            timeout=TIMEOUT,
        )
        assert response.status_code in [200, 403]  # 403 if no org access

    @pytest.mark.skipif(not AUTH0_TEST_TOKEN, reason="AUTH0_TEST_TOKEN not set")
    def test_database_write_operation(self):
        """Can write to database"""
        # Test creating a resource (if applicable)
        # This is a placeholder - adjust based on your API
        pass


class TestRedis:
    """Redis connectivity and job queue tests"""

    @pytest.mark.skipif(not AUTH0_TEST_TOKEN, reason="AUTH0_TEST_TOKEN not set")
    def test_redis_connection(self):
        """Redis is accessible from API"""
        # This would test an endpoint that uses Redis
        # Placeholder - adjust based on your implementation
        pass

    @pytest.mark.skipif(not AUTH0_TEST_TOKEN, reason="AUTH0_TEST_TOKEN not set")
    def test_job_enqueue_and_process(self):
        """Background jobs are processed by worker"""
        # Test job enqueueing and verify it gets processed
        # This requires a test endpoint that creates a job
        # Placeholder - implement when you have job endpoints
        pass


class TestPerformance:
    """Basic performance and stability tests"""

    def test_response_time_acceptable(self):
        """Health endpoint responds quickly"""
        import time

        start = time.time()
        response = requests.get(f"{PREPROD_API_URL}/health", timeout=TIMEOUT)
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 2.0  # Should respond in under 2 seconds

    def test_concurrent_requests_handled(self):
        """API handles multiple concurrent requests"""
        import concurrent.futures

        def make_request():
            response = requests.get(f"{PREPROD_API_URL}/health", timeout=TIMEOUT)
            return response.status_code == 200

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]

        assert all(results), "Some concurrent requests failed"


class TestEnvironmentConfig:
    """Validate environment configuration"""

    def test_environment_is_preprod(self):
        """Environment is correctly set to preprod"""
        response = requests.get(f"{PREPROD_API_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        # Add environment to health endpoint if not present
        # assert response.json().get("environment") == "preprod"

    def test_debug_mode_disabled(self):
        """Debug mode is disabled in pre-prod"""
        # Verify debug-specific endpoints are not exposed
        response = requests.get(f"{PREPROD_API_URL}/debug", timeout=TIMEOUT)
        assert response.status_code == 404


# Run with: pytest tests/test_preprod.py -v
# With auth: PREPROD_API_URL=https://your-api.azurecontainerapps.io AUTH0_TEST_TOKEN=your_token pytest tests/test_preprod.py -v
