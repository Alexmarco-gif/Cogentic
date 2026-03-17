"""Industry taxonomy model (4 root industries + sub-verticals)"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.entity import Entity
    from backend.models.intelligence_brief import IntelligenceBrief
    from backend.models.signal_contract import SignalContract


class Industry(Base, UUIDMixin, TimestampMixin):
    """Industry taxonomy with hierarchical structure.

    Root industries (4):
      - E-Commerce / FMCG / Retail
      - Financial Services & Fintech
      - Media / Marketing / Consumer & Brand
      - Telecom / Digital Services / Infrastructure

    Each root has sub-verticals as children.
    """

    __tablename__ = "industries"

    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default="{}", name="metadata"
    )

    # Self-referential relationships
    children: Mapped[list["Industry"]] = relationship(
        "Industry",
        back_populates="parent",
    )
    parent: Mapped["Industry | None"] = relationship(
        "Industry",
        back_populates="children",
        remote_side="Industry.id",
    )

    # Downstream relationships
    entities: Mapped[list["Entity"]] = relationship(
        back_populates="industry",
    )
    signal_contracts: Mapped[list["SignalContract"]] = relationship(
        back_populates="industry",
    )
    briefs: Mapped[list["IntelligenceBrief"]] = relationship(
        back_populates="industry",
    )

    def __repr__(self) -> str:
        return f"<Industry {self.slug}>"
