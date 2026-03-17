"""Signal-Entity many-to-many join table"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.entity import Entity
    from backend.models.signal import Signal


class SignalEntity(Base, UUIDMixin, TimestampMixin):
    """Many-to-many relationship between signals and entities with relevance scoring."""

    __tablename__ = "signal_entities"
    __table_args__ = (
        UniqueConstraint("signal_id", "entity_id", name="uq_signal_entity"),
    )

    signal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relevance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )  # 0.0 to 1.0

    # Relationships
    signal: Mapped["Signal"] = relationship(back_populates="entity_links")
    entity: Mapped["Entity"] = relationship(back_populates="signal_links")

    def __repr__(self) -> str:
        return f"<SignalEntity signal={self.signal_id} entity={self.entity_id} score={self.relevance_score}>"
