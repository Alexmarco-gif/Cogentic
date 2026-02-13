"""Entity alias model — alternate names for canonical entities."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.entity import Entity


class EntityAlias(Base, UUIDMixin, TimestampMixin):
    """Alternate names / synonyms for a canonical entity.

    alias_type values:
      - legal_name: Official registered name (e.g., CAC Nigeria)
      - trading_name: Name used in commerce
      - abbreviation: Acronym or short form (e.g., "DIL" for Dangote Industries)
      - former_name: Previous name (e.g., after rebranding)
      - local_name: Region-specific name (e.g., local language)
      - ticker: Stock exchange ticker symbol

    source: Where the alias was discovered (e.g., cac_nigeria, linkedin, manual)
    """

    __tablename__ = "entity_aliases"

    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    alias_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Relationships
    entity: Mapped["Entity"] = relationship(
        back_populates="alias_records",
    )

    def __repr__(self) -> str:
        return f"<EntityAlias '{self.alias_name}' type={self.alias_type}>"
