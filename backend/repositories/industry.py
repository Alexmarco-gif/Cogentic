"""Industry repository"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.industry import Industry
from backend.repositories.base import BaseRepository


class IndustryRepository(BaseRepository[Industry]):
    """Repository for industry taxonomy operations.

    Industries are global (not tenant-scoped). Uses BaseRepository.
    Supports hierarchical structure (parent_id for sub-verticals).
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Industry, db)

    async def get_by_slug(self, slug: str) -> Industry | None:
        """Get industry by slug"""
        result = await self.db.execute(select(Industry).where(Industry.slug == slug))
        return result.scalar_one_or_none()

    async def get_root_industries(self) -> list[Industry]:
        """Get all root industries (parent_id=NULL) — the 4 launch industries"""
        result = await self.db.execute(
            select(Industry).where(Industry.parent_id.is_(None)).order_by(Industry.name)
        )
        return list(result.scalars().all())

    async def get_with_children(self, industry_id: UUID) -> Industry | None:
        """Get industry with eager-loaded children (sub-verticals)"""
        result = await self.db.execute(
            select(Industry)
            .options(selectinload(Industry.children))
            .where(Industry.id == industry_id)
        )
        return result.scalar_one_or_none()

    async def get_children(self, parent_id: UUID) -> list[Industry]:
        """Get all sub-verticals of a parent industry"""
        result = await self.db.execute(
            select(Industry)
            .where(Industry.parent_id == parent_id)
            .order_by(Industry.name)
        )
        return list(result.scalars().all())

    async def get_full_tree(self) -> list[Industry]:
        """Get all root industries with their children pre-loaded"""
        result = await self.db.execute(
            select(Industry)
            .options(selectinload(Industry.children))
            .where(Industry.parent_id.is_(None))
            .order_by(Industry.name)
        )
        return list(result.scalars().all())

    async def slug_exists(self, slug: str) -> bool:
        """Check if slug is already taken"""
        industry = await self.get_by_slug(slug)
        return industry is not None
