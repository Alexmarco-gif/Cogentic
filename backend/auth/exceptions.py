"""
Custom exceptions for authentication and authorization.

These exceptions are caught by FastAPI exception handlers to return
appropriate HTTP responses.
"""

from typing import Any


class AuthError(Exception):
    """
    Base authentication error.

    Returns 401 Unauthorized with generic message to client.
    Details logged server-side for debugging.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class InvalidTokenError(AuthError):
    """Token is malformed or has invalid signature"""

    def __init__(self, reason: str, details: dict[str, Any] | None = None):
        super().__init__(
            message="Invalid token", details={"reason": reason, **(details or {})}
        )


class TokenExpiredError(AuthError):
    """Token has expired"""

    def __init__(self, expired_at: str, details: dict[str, Any] | None = None):
        super().__init__(
            message="Token expired",
            details={"expired_at": expired_at, **(details or {})},
        )


class MissingTokenError(AuthError):
    """No token provided in request"""

    def __init__(self):
        super().__init__(
            message="Missing authentication token",
            details={"hint": "Include Bearer token in Authorization header"},
        )


class InvalidClaimsError(AuthError):
    """Required custom claims missing from token"""

    def __init__(self, missing_claims: list[str]):
        super().__init__(
            message="Invalid token claims", details={"missing_claims": missing_claims}
        )


class ForbiddenError(Exception):
    """
    Authorization error (authenticated but not authorized).

    Returns 403 Forbidden.
    """

    def __init__(
        self, message: str = "Access denied", details: dict[str, Any] | None = None
    ):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class InsufficientRoleError(ForbiddenError):
    """User role insufficient for requested action"""

    def __init__(self, required_role: str, current_role: str):
        super().__init__(
            message="Insufficient permissions",
            details={"required_role": required_role, "current_role": current_role},
        )


class NotOrgMemberError(ForbiddenError):
    """User not a member of the requested organization"""

    def __init__(self, org_id: str):
        super().__init__(
            message="Access denied to organization", details={"org_id": org_id}
        )


class NotResourceOwnerError(ForbiddenError):
    """User does not own the requested resource"""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"Access denied to {resource_type}",
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class FeatureDisabledError(ForbiddenError):
    """Feature is disabled or not available for user's plan"""

    def __init__(self, feature_name: str, reason: str = "Feature not available"):
        super().__init__(
            message=f"Feature '{feature_name}' is not available",
            details={"feature": feature_name, "reason": reason},
        )
