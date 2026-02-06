"""
Pytest Configuration for E2E Tests
===================================

Provides shared fixtures, configuration, and utilities for end-to-end testing
against the live pre-prod API.

Usage:
    PREPROD_API_URL=https://your-api.azurecontainerapps.io pytest backend/tests/ -v -m "e2e"

With authentication:
    AUTH0_TEST_TOKEN=your_token pytest backend/tests/ -v -m "e2e"
"""

import os
import socket
import sys
from pathlib import Path
from urllib.parse import urljoin

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


# =============================================================================
# Configuration
# =============================================================================

# Default pre-prod URL (can be overridden via environment variable)
DEFAULT_PREPROD_URL = (
    "https://cogent-api.yellowtree-0cde5f74.eastus.azurecontainerapps.io"
)

# Test timeouts (Azure Container Apps can have cold starts)
DEFAULT_TIMEOUT = 30
LONG_TIMEOUT = 60


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "e2e: End-to-end tests hitting live API")
    config.addinivalue_line(
        "markers", "smoke: Quick smoke tests for deployment validation"
    )
    config.addinivalue_line("markers", "auth: Tests requiring authentication")
    config.addinivalue_line("markers", "security: Security-focused tests")


# =============================================================================
# IPv4 Fix for Windows (Azure Container Apps issue)
# =============================================================================


def _force_ipv4():
    """Force IPv4 connections to avoid Windows IPv6 issues with Azure"""
    _original_getaddrinfo = socket.getaddrinfo

    def _getaddrinfo_ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
        return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

    socket.getaddrinfo = _getaddrinfo_ipv4_only


# Apply IPv4 fix
_force_ipv4()


# =============================================================================
# HTTP Session with Retry Logic
# =============================================================================


def create_session() -> requests.Session:
    """
    Create a requests session with retry logic for resilience.

    Handles:
    - Connection errors
    - 5xx server errors
    - Rate limiting (429)
    - Azure Container Apps cold starts
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10,
    )

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


# =============================================================================
# Session-Scoped Fixtures (shared across all tests in session)
# =============================================================================


@pytest.fixture(scope="session")
def api_url() -> str:
    """
    Get the pre-prod API base URL.

    Set via PREPROD_API_URL environment variable or uses default.
    """
    url = os.getenv("PREPROD_API_URL", DEFAULT_PREPROD_URL)
    # Ensure no trailing slash
    return url.rstrip("/")


@pytest.fixture(scope="session")
def auth_token() -> str | None:
    """
    Get Auth0 test token from environment.

    Set via AUTH0_TEST_TOKEN environment variable.
    Returns None if not set (tests requiring auth will be skipped).
    """
    return os.getenv("AUTH0_TEST_TOKEN")


@pytest.fixture(scope="session")
def auth_token_valid(auth_token, http_session, api_url) -> bool:
    """
    Validate the auth token once per session.

    Returns True if token works against /api/v1/auth/me, else False.
    """
    if not auth_token:
        return False

    try:
        response = http_session.get(
            urljoin(api_url + "/", "/api/v1/auth/me"),
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException:
        return False

    return response.status_code == 200


@pytest.fixture(scope="session")
def http_session() -> requests.Session:
    """
    Shared HTTP session with retry logic.

    Reused across all tests for connection pooling efficiency.
    """
    return create_session()


# =============================================================================
# Function-Scoped Fixtures (fresh for each test)
# =============================================================================


@pytest.fixture
def client(http_session, api_url):
    """
    API client wrapper for making requests.

    Provides convenient methods for API calls with automatic URL joining.
    """

    class APIClient:
        def __init__(self, session: requests.Session, base_url: str):
            self.session = session
            self.base_url = base_url
            self.timeout = DEFAULT_TIMEOUT

        def url(self, path: str) -> str:
            """Join base URL with path"""
            return urljoin(self.base_url + "/", path.lstrip("/"))

        def get(self, path: str, **kwargs) -> requests.Response:
            kwargs.setdefault("timeout", self.timeout)
            return self.session.get(self.url(path), **kwargs)

        def post(self, path: str, **kwargs) -> requests.Response:
            kwargs.setdefault("timeout", self.timeout)
            return self.session.post(self.url(path), **kwargs)

        def patch(self, path: str, **kwargs) -> requests.Response:
            kwargs.setdefault("timeout", self.timeout)
            return self.session.patch(self.url(path), **kwargs)

        def delete(self, path: str, **kwargs) -> requests.Response:
            kwargs.setdefault("timeout", self.timeout)
            return self.session.delete(self.url(path), **kwargs)

        def options(self, path: str, **kwargs) -> requests.Response:
            kwargs.setdefault("timeout", self.timeout)
            return self.session.options(self.url(path), **kwargs)

    return APIClient(http_session, api_url)


@pytest.fixture
def auth_headers(auth_token) -> dict[str, str]:
    """
    Authorization headers for authenticated requests.

    Returns empty dict if no token available.
    """
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}
    return {}


@pytest.fixture
def authed_client(client, auth_headers):
    """
    API client with authentication headers pre-configured.

    Wraps the base client to automatically include auth headers.
    """

    class AuthedAPIClient:
        def __init__(self, base_client, headers: dict):
            self._client = base_client
            self._auth_headers = headers

        def _merge_headers(self, kwargs: dict) -> dict:
            headers = kwargs.pop("headers", {})
            headers.update(self._auth_headers)
            kwargs["headers"] = headers
            return kwargs

        def get(self, path: str, **kwargs) -> requests.Response:
            return self._client.get(path, **self._merge_headers(kwargs))

        def post(self, path: str, **kwargs) -> requests.Response:
            return self._client.post(path, **self._merge_headers(kwargs))

        def patch(self, path: str, **kwargs) -> requests.Response:
            return self._client.patch(path, **self._merge_headers(kwargs))

        def delete(self, path: str, **kwargs) -> requests.Response:
            return self._client.delete(path, **self._merge_headers(kwargs))

    return AuthedAPIClient(client, auth_headers)


# =============================================================================
# Skip Markers
# =============================================================================


@pytest.fixture
def requires_auth(auth_token, auth_token_valid):
    """Skip test if no valid auth token available"""
    if not auth_token:
        pytest.skip("AUTH0_TEST_TOKEN not set - skipping authenticated test")
    if not auth_token_valid:
        pytest.skip("AUTH0_TEST_TOKEN invalid or expired - skipping authenticated test")


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def random_string():
    """Generate a random string for test data"""
    import uuid

    return str(uuid.uuid4())[:8]


@pytest.fixture
def test_document_data(random_string):
    """Sample document data for creation tests"""
    return {
        "filename": f"test_doc_{random_string}.pdf",
        "storage_path": f"/uploads/test_{random_string}.pdf",
        "size_bytes": 1024,
        "content_type": "application/pdf",
        "processing_status": "pending",
    }


@pytest.fixture
def test_api_key_data(random_string):
    """Sample API key data for creation tests"""
    return {
        "name": f"Test Key {random_string}",
        "description": "E2E test API key",
        "scopes": ["read:documents", "write:documents"],
        "rate_limit": 100,
    }
