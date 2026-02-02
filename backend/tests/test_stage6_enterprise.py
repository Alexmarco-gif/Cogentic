"""
Tests for Stage 6: Enterprise Features

Tests for:
- Rate limiting
- Admin override system
- API key authentication
"""

import hashlib
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from backend.auth.schemas import AuthContext
from backend.auth.guards import require_org_membership
from backend.auth.exceptions import NotOrgMemberError
from backend.models.api_key import APIKey
from backend.repositories.api_key import APIKeyRepository

# ============================================================================
# Rate Limiting Tests
# ============================================================================


class TestRateLimiting:
    """Test rate limiting configuration"""

    def test_rate_limit_key_authenticated(self):
        """Rate limit key should use user_id for authenticated requests"""
        from backend.auth.rate_limit import get_rate_limit_key
        from unittest.mock import Mock

        request = Mock()
        auth = AuthContext(
            user_id=uuid4(),
            auth0_id="auth0|123",
            email="test@example.com",
            org_id=uuid4(),
            role="member",
            plan="free",
            is_super_admin=False,
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            request_id="test-123",
        )
        request.state.auth = auth

        key = get_rate_limit_key(request)

        assert key.startswith("user:")
        assert str(auth.user_id) in key

    def test_rate_limit_key_unauthenticated(self):
        """Rate limit key should use IP for unauthenticated requests"""
        from backend.auth.rate_limit import get_rate_limit_key
        from unittest.mock import Mock

        request = Mock()
        request.state.auth = None
        request.client.host = "1.2.3.4"

        key = get_rate_limit_key(request)

        assert key.startswith("ip:")

    def test_rate_limit_for_super_admin(self):
        """Super admins should get highest rate limits"""
        from backend.auth.rate_limit import get_rate_limit_for_user
        from unittest.mock import Mock

        request = Mock()
        auth = AuthContext(
            user_id=uuid4(),
            auth0_id="auth0|123",
            email="admin@example.com",
            org_id=uuid4(),
            role="admin",
            plan="enterprise",
            is_super_admin=True,
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            request_id="test-123",
        )
        request.state.auth = auth

        limit = get_rate_limit_for_user(request)

        assert limit == "1000/minute"

    def test_rate_limit_for_admin(self):
        """Admins should get high rate limits"""
        from backend.auth.rate_limit import get_rate_limit_for_user
        from unittest.mock import Mock

        request = Mock()
        auth = AuthContext(
            user_id=uuid4(),
            auth0_id="auth0|123",
            email="admin@example.com",
            org_id=uuid4(),
            role="admin",
            plan="pro",
            is_super_admin=False,
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            request_id="test-123",
        )
        request.state.auth = auth

        limit = get_rate_limit_for_user(request)

        assert limit == "1000/minute"

    def test_rate_limit_for_regular_user(self):
        """Regular authenticated users should get standard limits"""
        from backend.auth.rate_limit import get_rate_limit_for_user
        from unittest.mock import Mock

        request = Mock()
        auth = AuthContext(
            user_id=uuid4(),
            auth0_id="auth0|123",
            email="user@example.com",
            org_id=uuid4(),
            role="member",
            plan="free",
            is_super_admin=False,
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            request_id="test-123",
        )
        request.state.auth = auth

        limit = get_rate_limit_for_user(request)

        assert limit == "100/minute"

    def test_rate_limit_for_unauthenticated(self):
        """Unauthenticated requests should get low limits"""
        from backend.auth.rate_limit import get_rate_limit_for_user
        from unittest.mock import Mock

        request = Mock()
        request.state.auth = None

        limit = get_rate_limit_for_user(request)

        assert limit == "20/minute"


# ============================================================================
# Admin Override Tests
# ============================================================================


class TestAdminOverride:
    """Test super admin override system"""

    def test_super_admin_can_bypass_org_check(self):
        """Super admins should be able to access any org"""
        org_id_a = uuid4()
        org_id_b = uuid4()

        auth = AuthContext(
            user_id=uuid4(),
            auth0_id="auth0|admin",
            email="admin@cogent.ai",
            org_id=org_id_a,
            role="admin",
            plan="enterprise",
            is_super_admin=True,
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            request_id="test-123",
        )

        # Should NOT raise exception (override)
        require_org_membership(auth, org_id_b)

    def test_regular_admin_cannot_bypass_org_check(self):
        """Regular admins should NOT be able to bypass org checks"""
        org_id_a = uuid4()
        org_id_b = uuid4()

        auth = AuthContext(
            user_id=uuid4(),
            auth0_id="auth0|admin",
            email="admin@example.com",
            org_id=org_id_a,
            role="admin",
            plan="pro",
            is_super_admin=False,
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            request_id="test-123",
        )

        # Should raise exception
        with pytest.raises(NotOrgMemberError):
            require_org_membership(auth, org_id_b)

    def test_super_admin_same_org_no_override(self):
        """Super admin accessing their own org should not trigger override logging"""
        org_id = uuid4()

        auth = AuthContext(
            user_id=uuid4(),
            auth0_id="auth0|admin",
            email="admin@cogent.ai",
            org_id=org_id,
            role="admin",
            plan="enterprise",
            is_super_admin=True,
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            request_id="test-123",
        )

        # Should pass normally (no override needed)
        require_org_membership(auth, org_id)


# ============================================================================
# API Key Model Tests
# ============================================================================


class TestAPIKeyModel:
    """Test API key model properties"""

    def test_api_key_active_when_not_revoked(self):
        """API key should be active when not revoked and not expired"""
        api_key = APIKey(
            id=uuid4(),
            key_hash="abc123",
            key_prefix="cogent_pk_live_",
            org_id=uuid4(),
            created_by_user_id=uuid4(),
            name="Test Key",
            scopes="read:documents,write:documents",
            rate_limit=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert api_key.is_active is True

    def test_api_key_inactive_when_revoked(self):
        """API key should be inactive when revoked"""
        api_key = APIKey(
            id=uuid4(),
            key_hash="abc123",
            key_prefix="cogent_pk_live_",
            org_id=uuid4(),
            created_by_user_id=uuid4(),
            name="Test Key",
            scopes="read:documents",
            rate_limit=100,
            revoked_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert api_key.is_active is False

    def test_api_key_inactive_when_expired(self):
        """API key should be inactive when expired"""
        api_key = APIKey(
            id=uuid4(),
            key_hash="abc123",
            key_prefix="cogent_pk_live_",
            org_id=uuid4(),
            created_by_user_id=uuid4(),
            name="Test Key",
            scopes="read:documents",
            rate_limit=100,
            expires_at=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert api_key.is_active is False

    def test_scopes_list_parsing(self):
        """Scopes should be parsed from comma-separated string"""
        api_key = APIKey(
            id=uuid4(),
            key_hash="abc123",
            key_prefix="cogent_pk_live_",
            org_id=uuid4(),
            created_by_user_id=uuid4(),
            name="Test Key",
            scopes="read:documents,write:documents,delete:documents",
            rate_limit=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert api_key.scopes_list == [
            "read:documents",
            "write:documents",
            "delete:documents",
        ]

    def test_has_scope(self):
        """Should correctly check if key has a scope"""
        api_key = APIKey(
            id=uuid4(),
            key_hash="abc123",
            key_prefix="cogent_pk_live_",
            org_id=uuid4(),
            created_by_user_id=uuid4(),
            name="Test Key",
            scopes="read:documents,write:documents",
            rate_limit=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert api_key.has_scope("read:documents") is True
        assert api_key.has_scope("write:documents") is True
        assert api_key.has_scope("delete:documents") is False


# ============================================================================
# API Key Repository Tests
# ============================================================================


class TestAPIKeyRepository:
    """Test API key repository operations"""

    def test_generate_key_format(self):
        """Generated keys should have correct format"""
        full_key, key_hash, key_prefix = APIKeyRepository.generate_key()

        # Check format
        assert full_key.startswith("cogent_pk_live_")
        assert len(full_key) > 30  # Should be long enough

        # Check hash is SHA256
        assert len(key_hash) == 64  # SHA256 hex digest length

        # Check prefix
        assert key_prefix == full_key[:16]

    def test_hash_key_consistency(self):
        """Same key should always hash to same value"""
        key = "cogent_pk_live_test123456"

        hash1 = APIKeyRepository.hash_key(key)
        hash2 = APIKeyRepository.hash_key(key)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_hash_key_correct_algorithm(self):
        """Key hashing should use SHA256"""
        key = "cogent_pk_live_test"
        expected = hashlib.sha256(key.encode()).hexdigest()

        actual = APIKeyRepository.hash_key(key)

        assert actual == expected


# ============================================================================
# Integration Test Stubs (require database)
# ============================================================================


class TestAPIKeyAuthenticationFlow:
    """Integration tests for API key authentication (require DB)"""

    @pytest.mark.skip(reason="Requires database setup")
    async def test_create_api_key_flow(self):
        """Test creating an API key through repository"""
        pass

    @pytest.mark.skip(reason="Requires database setup")
    async def test_authenticate_with_api_key(self):
        """Test authenticating with API key"""
        pass

    @pytest.mark.skip(reason="Requires database setup")
    async def test_api_key_last_used_at_updated(self):
        """Test last_used_at timestamp updates on use"""
        pass

    @pytest.mark.skip(reason="Requires database setup")
    async def test_revoked_key_rejected(self):
        """Test revoked API keys are rejected"""
        pass

    @pytest.mark.skip(reason="Requires database setup")
    async def test_expired_key_rejected(self):
        """Test expired API keys are rejected"""
        pass


class TestAPIKeyEndpoints:
    """Integration tests for API key management endpoints (require DB)"""

    @pytest.mark.skip(reason="Requires database setup")
    async def test_create_api_key_endpoint(self):
        """Test POST /api/v1/orgs/{org_id}/api-keys"""
        pass

    @pytest.mark.skip(reason="Requires database setup")
    async def test_list_api_keys_endpoint(self):
        """Test GET /api/v1/orgs/{org_id}/api-keys"""
        pass

    @pytest.mark.skip(reason="Requires database setup")
    async def test_revoke_api_key_endpoint(self):
        """Test DELETE /api/v1/orgs/{org_id}/api-keys/{key_id}"""
        pass

    @pytest.mark.skip(reason="Requires database setup")
    async def test_api_key_requires_admin(self):
        """Test API key endpoints require admin role"""
        pass

    @pytest.mark.skip(reason="Requires database setup")
    async def test_api_key_max_limit_enforced(self):
        """Test max 50 API keys per org limit"""
        pass
