"""Document model (files uploaded by users)"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.organization import Organization
    from backend.models.user import User


class Document(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """User-uploaded files for AI processing (future: stored in blob storage)"""

    __tablename__ = "documents"

    # Multi-tenant isolation
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    # File metadata
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Storage location (future: Azure Blob Storage URLs)
    # For MVP: files stored locally or in temp storage
    storage_path: Mapped[str | None] = mapped_column(Text)

    # AI processing
    processing_status: Mapped[str] = mapped_column(
        String(50), default="pending", index=True
    )  # pending, processing, completed, failed
    extracted_text: Mapped[str | None] = mapped_column(Text)

    # pgvector embedding (for semantic search)
    # Note: This will be added via migration when we implement AI features
    # embedding: Mapped[Vector | None] = mapped_column(Vector(1536))

    # Sharing & permissions
    visibility: Mapped[str] = mapped_column(
        String(50), default="private"
    )  # private, org, shared
    shared_with: Mapped[list] = mapped_column(
        JSON, default=list, server_default="[]"
    )  # Array of user IDs

    # GDPR compliance (auto-delete)
    retention_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    organization: Mapped["Organization"] = relationship()
    owner: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<Document {self.filename} org={self.org_id}>"
