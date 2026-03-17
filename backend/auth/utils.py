"""
Utility functions for JWT token handling and validation.
"""

import logging
from datetime import datetime, timezone

from fastapi import Request
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

from backend.auth.exceptions import (
    InvalidClaimsError,
    InvalidTokenError,
    MissingTokenError,
    TokenExpiredError,
)
from backend.auth.jwks import get_jwks_client
from backend.auth.schemas import TokenPayload
from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def extract_token_from_header(request: Request) -> str:
    """
    Extract Bearer token from Authorization header.

    Args:
        request: FastAPI request object

    Returns:
        JWT token string (without "Bearer " prefix)

    Raises:
        MissingTokenError: If Authorization header missing or malformed
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        logger.warning("Missing Authorization header")
        raise MissingTokenError()

    parts = auth_header.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Malformed Authorization header: {auth_header[:20]}...")
        raise InvalidTokenError("Malformed Authorization header")

    return parts[1]


async def verify_token(token: str) -> TokenPayload:
    """
    Verify JWT token signature and claims.

    Steps:
    1. Decode header to get key ID (kid)
    2. Fetch public key from JWKS
    3. Verify signature
    4. Validate claims (issuer, audience, expiration)
    5. Parse custom claims

    Args:
        token: JWT token string

    Returns:
        Validated token payload with custom claims

    Raises:
        InvalidTokenError: If signature invalid or claims missing
        TokenExpiredError: If token expired
    """
    try:
        # Decode header without verification to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            logger.error("Token missing kid in header")
            raise InvalidTokenError("Token missing key ID")

        # Get signing key from JWKS
        jwks_client = await get_jwks_client()
        signing_key = await jwks_client.get_signing_key(kid)

        # Verify signature and decode payload
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )

        # Parse into validated model
        token_payload = TokenPayload(**payload)

        logger.debug(f"Token verified for user: {token_payload.sub}")
        return token_payload

    except ExpiredSignatureError as e:
        logger.warning("Token expired")
        raise TokenExpiredError(
            expired_at=datetime.now(timezone.utc).isoformat()
        ) from e

    except JWTClaimsError as e:
        logger.error(f"JWT claims validation failed: {e}")
        raise InvalidTokenError(f"Invalid JWT claims: {e}") from e

    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise InvalidTokenError(f"Token verification failed: {e}") from e

    except ValueError as e:
        logger.error(f"JWKS error: {e}")
        raise InvalidTokenError(f"Failed to verify token signature: {e}") from e

    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}", exc_info=True)
        raise InvalidTokenError(f"Token verification failed: {e}") from e


def validate_custom_claims(payload: TokenPayload) -> None:
    """
    Validate that required custom claims are present.

    For regular (user) tokens:
    - org_id: User's primary organization
    - roles: User's roles (can be empty for viewer)
    - plan: Organization's subscription plan

    For M2M (client-credentials) tokens:
    - org_id: Organization the service account acts on behalf of
    - user_id: Service user ID (from Auth0 Action)
    - role: Role for the service account

    Args:
        payload: Validated token payload

    Raises:
        InvalidClaimsError: If required claims missing
    """
    missing_claims = []
    fields_set = getattr(payload, "model_fields_set", set())

    # M2M tokens have different claim requirements
    if payload.is_m2m_token:
        # M2M tokens need org_id, user_id, and role from Auth0 Action
        if not payload.org_id:
            missing_claims.append("org_id")
        if not payload.user_id:
            missing_claims.append("user_id")
        if not payload.role:
            missing_claims.append("role")

        if missing_claims:
            logger.error(
                f"M2M token missing required claims: {missing_claims}. "
                "Configure Auth0 Client Credentials Exchange Action to add these claims."
            )
            raise InvalidClaimsError(missing_claims)
        return

    # Regular user tokens
    if not payload.org_id:
        missing_claims.append("org_id")

    # Note: roles can be empty list (valid for viewer), but must be present
    if "roles" not in fields_set:
        missing_claims.append("roles")

    # Note: plan has default value "explorer", but must be present
    if "plan" not in fields_set:
        missing_claims.append("plan")

    if missing_claims:
        logger.error(f"Token missing required claims: {missing_claims}")
        raise InvalidClaimsError(missing_claims)


def get_request_id(request: Request) -> str | None:
    """
    Extract X-Request-ID from request headers.

    Args:
        request: FastAPI request object

    Returns:
        Request ID if present, None otherwise
    """
    return request.headers.get("X-Request-ID")
