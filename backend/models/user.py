"""User model (shadow profile from Auth0)"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.org_user import OrgUser


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Local user cache synced from Auth0"""
    
    __tablename__ = "users"
    
    # Auth0 identity
    auth0_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    # Core identity (cached from Auth0)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    picture_url: Mapped[str | None] = mapped_column(String(500))
    
    # Local metadata
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    login_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # GDPR compliance
    data_processing_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    organizations: Mapped[list["OrgUser"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[OrgUser.user_id]"
    )
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
