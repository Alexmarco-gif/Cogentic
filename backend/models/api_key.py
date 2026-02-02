"""
API Key model for M2M authentication

Allows programmatic access to the API without user JWT tokens.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from backend.models.organization import Organization


class APIKey(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    API key for machine-to-machine authentication.

    Format: cogent_pk_live_{random_32_chars}
    Example: cogent_pk_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4
    """

    __tablename__ = "api_keys"

    # Identity (inherited from UUIDMixin)
    # id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Key data
    key_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True
    )  # SHA256 hash
    key_prefix: Mapped[str] = mapped_column(
        String(16), index=True
    )  # First 8 chars for identification

    # Ownership
    org_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Metadata
    name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # "Production API", "CI/CD Pipeline"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Permissions
    scopes: Mapped[str] = mapped_column(
        Text,  # Store as comma-separated string
        nullable=False,
        default="read:documents,write:documents",
    )

    # Rate limiting (requests per minute)
    rate_limit: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Lifecycle
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="api_keys"
    )

    @property
    def is_active(self) -> bool:
        """Check if API key is currently active"""
        now = datetime.utcnow()

        # Revoked keys are inactive
        if self.revoked_at is not None:
            return False

        # Expired keys are inactive
        if self.expires_at is not None and self.expires_at < now:
            return False

        return True

    @property
    def scopes_list(self) -> list[str]:
        """Parse scopes from comma-separated string"""
        if not self.scopes:
            return []
        return [s.strip() for s in self.scopes.split(",")]

    def has_scope(self, scope: str) -> bool:
        """Check if API key has a specific scope"""
        return scope in self.scopes_list

    def __repr__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return f"<APIKey {self.key_prefix}... org={self.org_id} status={status}>"
