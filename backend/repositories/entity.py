"""Entity repository"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.entity import Entity
from backend.models.signal_entity import SignalEntity
from backend.repositories.base import BaseRepository


class EntityRepository(BaseRepository[Entity]):
    """Repository for entity operations (companies, products, people, brands).

    Entities are global (not tenant-scoped). Uses BaseRepository.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Entity, db)

    async def get_by_name(self, name: str) -> Entity | None:
        """Get entity by exact name"""
        result = await self.db.execute(select(Entity).where(Entity.name == name))
        return result.scalar_one_or_none()

    async def get_by_industry(
        self,
        industry_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Entity]:
        """Get all entities for a given industry"""
        result = await self.db.execute(
            select(Entity)
            .where(Entity.industry_id == industry_id)
            .order_by(Entity.name)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_type(
        self,
        entity_type: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Entity]:
        """Get entities by type (company, product, person, brand)"""
        result = await self.db.execute(
            select(Entity)
            .where(Entity.entity_type == entity_type)
            .order_by(Entity.name)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_name(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> list[Entity]:
        """Search entities by name (case-insensitive ILIKE)"""
        result = await self.db.execute(
            select(Entity)
            .where(Entity.name.ilike(f"%{query}%"))
            .order_by(Entity.name)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_industry_and_type(
        self,
        industry_id: UUID,
        entity_type: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Entity]:
        """Get entities filtered by both industry and type"""
        result = await self.db.execute(
            select(Entity)
            .where(
                Entity.industry_id == industry_id,
                Entity.entity_type == entity_type,
            )
            .order_by(Entity.name)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_signal_count(self, entity_id: UUID) -> int:
        """Count signals linked to this entity"""
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count(SignalEntity.id)).where(
                SignalEntity.entity_id == entity_id
            )
        )
        return result.scalar_one()
