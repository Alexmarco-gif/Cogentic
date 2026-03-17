"""Recommendation model — precomputed suggestions"""

from uuid import UUID

from sqlalchemy import Float, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, UUIDMixin


class Recommendation(Base, UUIDMixin, TimestampMixin):
    """Precomputed recommendation suggestions.

    Polymorphic source/target: can link signals, briefs, or entities.
    Used for "Related signals" and "You might also need" features.
    """

    __tablename__ = "recommendations"

    # Polymorphic source (signal, brief, entity)
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # signal, brief, entity
    source_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )

    # Polymorphic target
    target_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # signal, brief, entity
    target_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )

    # Scoring
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    algorithm_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Recommendation {self.source_type}→{self.target_type} score={self.score}>"
        )
