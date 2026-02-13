"""Entity model (companies, products, people, brands)"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.models.entity_alias import EntityAlias
    from backend.models.entity_relationship import EntityRelationship
    from backend.models.entity_source_profile import EntitySourceProfile
    from backend.models.industry import Industry
    from backend.models.signal_entity import SignalEntity


class Entity(Base, UUIDMixin, TimestampMixin):
    """Companies, products, people, brands tracked across industries.

    Each entity belongs to an industry and can be linked to multiple signals
    via the signal_entities join table.

    Entity Resolution 2.0 additions:
      - alias_records: Structured aliases (EntityAlias model)
      - source_profiles: Cross-source data fusion layer
      - outgoing_relationships / incoming_relationships: Entity graph edges
      - verified: Manual verification flag
    """

    __tablename__ = "entities"

    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # company, product, person, brand, infrastructure, cooperative
    industry_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("industries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    aliases: Mapped[list] = mapped_column(
        JSON, default=list, server_default="[]"
    )  # Legacy: simple alias list (kept for backward compat)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default="{}", name="metadata"
    )

    # Entity Resolution 2.0 fields
    verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # pgvector embedding (text-embedding-3-small, 1536 dimensions)
    embedding: Mapped[Any | None] = mapped_column(Vector(1536), nullable=True)

    # Relationships
    industry: Mapped["Industry | None"] = relationship(
        back_populates="entities",
    )
    signal_links: Mapped[list["SignalEntity"]] = relationship(
        back_populates="entity",
        cascade="all, delete-orphan",
    )

    # Entity Resolution 2.0 relationships
    alias_records: Mapped[list["EntityAlias"]] = relationship(
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    source_profiles: Mapped[list["EntitySourceProfile"]] = relationship(
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    outgoing_relationships: Mapped[list["EntityRelationship"]] = relationship(
        foreign_keys="EntityRelationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan",
    )
    incoming_relationships: Mapped[list["EntityRelationship"]] = relationship(
        foreign_keys="EntityRelationship.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Entity {self.name} type={self.entity_type}>"
