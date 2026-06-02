"""
Authentication schemas and models

Defines the structure of JWT claims and auth context used throughout the application.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TokenPayload(BaseModel):
    """Raw JWT token payload from Auth0"""

    model_config = ConfigDict(populate_by_name=True)

    # Standard JWT claims
    iss: str = Field(..., description="Issuer (Auth0 domain)")
    sub: str = Field(..., description="Subject (Auth0 user ID or client ID for M2M)")
    aud: str | list[str] = Field(..., description="Audience")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    azp: str | None = Field(None, description="Authorized party")
    scope: str | None = Field(None, description="OAuth scopes")
    gty: str | None = Field(None, description="Grant type (client-credentials for M2M)")

    # Custom claims (namespaced) - set by Auth0 Actions
    # Namespace: https://cogent.ai/claims/
    org_id: str | None = Field(None, alias="https://cogent.ai/claims/org_id")
    user_id: str | None = Field(None, alias="https://cogent.ai/claims/user_id")
    email: str | None = Field(None, alias="https://cogent.ai/claims/email")
    roles: list[str] = Field(
        default_factory=list, alias="https://cogent.ai/claims/roles"
    )
    role: str | None = Field(None, alias="https://cogent.ai/claims/role")
    plan: Literal["explorer", "growth", "mid_market", "enterprise"] = Field(
        "explorer", alias="https://cogent.ai/claims/plan"
    )
    is_super_admin: bool = Field(False, alias="https://cogent.ai/claims/is_super_admin")

    @property
    def is_m2m_token(self) -> bool:
        """Check if this is a machine-to-machine (client credentials) token"""
        return self.gty == "client-credentials"


class AuthContext(BaseModel):
    """
    Authentication context injected into request handlers via Depends(get_current_user).

    Contains all information needed for authorization decisions.
    """

    # Identity (from local DB after Auth0 sync)
    user_id: UUID = Field(..., description="Local user UUID")
    auth0_id: str = Field(..., description="Auth0 user ID")
    email: str = Field(..., description="User email")

    # Multi-tenant context
    org_id: UUID = Field(..., description="Current organization ID")

    # Authorization
    role: str = Field(
        ..., description="User role in current org (owner/admin/analyst/member/viewer)"
    )
    plan: Literal["explorer", "growth", "mid_market", "enterprise"] = Field(
        "explorer", description="Organization plan"
    )
    is_super_admin: bool = Field(
        False, description="Whether user is a super admin with override privileges"
    )

    # Token metadata
    token_expires_at: datetime = Field(..., description="Token expiration time")

    # Request metadata
    request_id: str | None = Field(None, description="X-Request-ID for tracing")
    auth_method: Literal["jwt", "api_key"] = Field(
        "jwt", description="Credential type used for this request"
    )
    api_key_id: UUID | None = Field(None, description="API key ID when auth_method=api_key")
    api_key_scopes: list[str] = Field(default_factory=list)

    @property
    def is_owner(self) -> bool:
        """Check if user is an owner"""
        return self.role == "owner"

    @property
    def is_admin_or_higher(self) -> bool:
        """Check if user is admin or owner (or super admin)"""
        return self.is_super_admin or self.role in ("owner", "admin")

    @property
    def is_member_or_higher(self) -> bool:
        """Check if user is member/analyst or higher (member, analyst, admin, owner)"""
        return self.role in ("owner", "admin", "analyst", "member")

    def __repr__(self) -> str:
        return f"<AuthContext user={self.user_id} org={self.org_id} role={self.role}>"
