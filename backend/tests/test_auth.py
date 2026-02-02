"""
Unit tests for authentication module.

Tests JWT verification, token validation, and error handling.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from jose import jwt

from backend.auth.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    MissingTokenError,
    InvalidClaimsError,
)
from backend.auth.schemas import TokenPayload, JWTClaims, AuthContext
from backend.auth.utils import (
    extract_token_from_header,
    verify_token,
    validate_custom_claims,
    parse_jwt_claims,
)
from backend.config import get_settings

settings = get_settings()


# Test data
TEST_AUTH0_ID = "auth0|12345"
TEST_EMAIL = "test@example.com"
TEST_ORG_ID = str(uuid4())
TEST_USER_ID = uuid4()


def create_mock_token(
    sub: str = TEST_AUTH0_ID,
    org_id: str = TEST_ORG_ID,
    roles: list[str] = None,
    plan: str = "free",
    expired: bool = False,
    missing_claims: list[str] = None,
) -> str:
    """Create a mock JWT token for testing"""
    
    if roles is None:
        roles = ["member"]
    
    now = int(datetime.utcnow().timestamp())
    exp = now - 3600 if expired else now + 3600
    
    payload = {
        "iss": f"https://{settings.auth0_domain}/",
        "sub": sub,
        "aud": settings.auth0_audience,
        "exp": exp,
        "iat": now,
    }
    
    # Add custom claims (unless testing missing claims)
    missing = missing_claims or []
    
    if "org_id" not in missing:
        payload["https://cogent-ai.com/org_id"] = org_id
    
    if "roles" not in missing:
        payload["https://cogent-ai.com/roles"] = roles
    
    if "plan" not in missing:
        payload["https://cogent-ai.com/plan"] = plan
    
    # Note: This creates an unsigned token for testing
    # In real tests with signature verification, you'd use a test private key
    return jwt.encode(payload, "test-secret", algorithm="HS256")


class TestExtractTokenFromHeader:
    """Test token extraction from Authorization header"""
    
    def test_extract_valid_bearer_token(self):
        """Should extract token from valid Bearer header"""
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer test_token_123"}
        
        token = extract_token_from_header(mock_request)
        assert token == "test_token_123"
    
    def test_missing_authorization_header(self):
        """Should raise MissingTokenError if header missing"""
        mock_request = MagicMock()
        mock_request.headers = {}
        
        with pytest.raises(MissingTokenError):
            extract_token_from_header(mock_request)
    
    def test_malformed_authorization_header_no_bearer(self):
        """Should raise InvalidTokenError if not Bearer scheme"""
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Basic test_token"}
        
        with pytest.raises(InvalidTokenError, match="Invalid token"):
            extract_token_from_header(mock_request)
    
    def test_malformed_authorization_header_no_token(self):
        """Should raise InvalidTokenError if token missing"""
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer"}
        
        with pytest.raises(InvalidTokenError, match="Invalid token"):
            extract_token_from_header(mock_request)


class TestValidateCustomClaims:
    """Test custom claims validation"""
    
    def test_valid_claims(self):
        """Should pass with all required claims"""
        payload = TokenPayload(
            iss=f"https://{settings.auth0_domain}/",
            sub=TEST_AUTH0_ID,
            aud=settings.auth0_audience,
            exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            iat=int(datetime.utcnow().timestamp()),
            org_id=TEST_ORG_ID,
            roles=["member"],
            plan="free",
        )
        
        # Should not raise
        validate_custom_claims(payload)
    
    def test_missing_org_id(self):
        """Should raise InvalidClaimsError if org_id missing"""
        payload = TokenPayload(
            iss=f"https://{settings.auth0_domain}/",
            sub=TEST_AUTH0_ID,
            aud=settings.auth0_audience,
            exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            iat=int(datetime.utcnow().timestamp()),
            org_id=None,
            roles=["member"],
            plan="free",
        )
        
        with pytest.raises(InvalidClaimsError) as exc_info:
            validate_custom_claims(payload)
        
        assert "org_id" in exc_info.value.details["missing_claims"]
    
    def test_empty_roles_allowed(self):
        """Should allow empty roles (valid for viewer)"""
        payload = TokenPayload(
            iss=f"https://{settings.auth0_domain}/",
            sub=TEST_AUTH0_ID,
            aud=settings.auth0_audience,
            exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            iat=int(datetime.utcnow().timestamp()),
            org_id=TEST_ORG_ID,
            roles=[],
            plan="free",
        )
        
        # Should not raise
        validate_custom_claims(payload)


class TestParseJWTClaims:
    """Test JWT claims parsing"""
    
    def test_parse_valid_payload(self):
        """Should parse TokenPayload to JWTClaims"""
        now = datetime.utcnow()
        exp = now + timedelta(hours=1)
        
        payload = TokenPayload(
            iss=f"https://{settings.auth0_domain}/",
            sub=TEST_AUTH0_ID,
            aud=settings.auth0_audience,
            exp=int(exp.timestamp()),
            iat=int(now.timestamp()),
            org_id=TEST_ORG_ID,
            roles=["admin", "member"],
            plan="pro",
        )
        
        claims = parse_jwt_claims(payload)
        
        assert isinstance(claims, JWTClaims)
        assert claims.auth0_id == TEST_AUTH0_ID
        assert str(claims.org_id) == TEST_ORG_ID
        assert claims.roles == ["admin", "member"]
        assert claims.plan == "pro"
        assert claims.issued_at.timestamp() == pytest.approx(now.timestamp(), abs=1)
        assert claims.expires_at.timestamp() == pytest.approx(exp.timestamp(), abs=1)


class TestAuthContext:
    """Test AuthContext model"""
    
    def test_create_auth_context(self):
        """Should create valid AuthContext"""
        context = AuthContext(
            user_id=TEST_USER_ID,
            auth0_id=TEST_AUTH0_ID,
            email=TEST_EMAIL,
            org_id=uuid4(),
            role="admin",
            plan="pro",
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        
        assert context.user_id == TEST_USER_ID
        assert context.role == "admin"
        assert context.plan == "pro"
    
    def test_is_owner_property(self):
        """Should correctly identify owner role"""
        context = AuthContext(
            user_id=TEST_USER_ID,
            auth0_id=TEST_AUTH0_ID,
            email=TEST_EMAIL,
            org_id=uuid4(),
            role="owner",
            plan="free",
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        
        assert context.is_owner is True
        assert context.is_admin_or_higher is True
        assert context.is_member_or_higher is True
    
    def test_is_admin_or_higher_property(self):
        """Should correctly identify admin+ roles"""
        admin_context = AuthContext(
            user_id=TEST_USER_ID,
            auth0_id=TEST_AUTH0_ID,
            email=TEST_EMAIL,
            org_id=uuid4(),
            role="admin",
            plan="free",
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        
        member_context = AuthContext(
            user_id=TEST_USER_ID,
            auth0_id=TEST_AUTH0_ID,
            email=TEST_EMAIL,
            org_id=uuid4(),
            role="member",
            plan="free",
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        
        assert admin_context.is_admin_or_higher is True
        assert member_context.is_admin_or_higher is False
    
    def test_is_member_or_higher_property(self):
        """Should correctly identify member+ roles"""
        member_context = AuthContext(
            user_id=TEST_USER_ID,
            auth0_id=TEST_AUTH0_ID,
            email=TEST_EMAIL,
            org_id=uuid4(),
            role="member",
            plan="free",
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        
        viewer_context = AuthContext(
            user_id=TEST_USER_ID,
            auth0_id=TEST_AUTH0_ID,
            email=TEST_EMAIL,
            org_id=uuid4(),
            role="viewer",
            plan="free",
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        
        assert member_context.is_member_or_higher is True
        assert viewer_context.is_member_or_higher is False


# Integration tests would go here (requires test Auth0 tenant)
# For now, we've covered unit tests for core functionality


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
