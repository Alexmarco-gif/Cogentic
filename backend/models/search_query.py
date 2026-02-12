"""Search Query model — Deep Live Search log & cache"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.organization import Organization
    from backend.models.user import User


class SearchQuery(Base, UUIDMixin, TimestampMixin):
    """Deep Live Search query log and result cache.

    Stores user search queries and synthesized results.
    query_hash (SHA-256) enables Redis-level caching (15min TTL)
    and DB-level result reuse.
    """

    __tablename__ = "search_queries"

    # Scoping
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Query
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )  # SHA-256 for cache lookup

    # Results
    results_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship()
    organization: Mapped["Organization"] = relationship()

    def __repr__(self) -> str:
        return f"<SearchQuery user={self.user_id} sources={self.source_count}>"
