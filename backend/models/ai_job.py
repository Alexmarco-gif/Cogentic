"""AI Job model (async processing tasks)"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.document import Document
    from backend.models.organization import Organization
    from backend.models.user import User


class AIJob(Base, UUIDMixin, TimestampMixin):
    """Async AI processing jobs (text extraction, embeddings, analysis)"""

    __tablename__ = "ai_jobs"

    # Multi-tenant isolation
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    document_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        index=True,
    )

    # Job configuration
    job_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # extract_text, generate_embedding, analyze_document
    input_params: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")

    # Execution tracking
    status: Mapped[str] = mapped_column(
        String(50), default="queued", index=True
    )  # queued, running, completed, failed
    priority: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)

    # Results
    result: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    # Relationships
    organization: Mapped["Organization"] = relationship()
    user: Mapped["User | None"] = relationship()
    document: Mapped["Document | None"] = relationship()

    def __repr__(self) -> str:
        return f"<AIJob {self.job_type} status={self.status}>"
