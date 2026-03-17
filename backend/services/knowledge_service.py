"""Knowledge Base CRUD service.

Provides async helpers for querying KnowledgeEntry rows.
Used by regulatory_intelligence.py and other services that need
domain-agnostic lookup data.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.knowledge_entry import KnowledgeEntry

logger = logging.getLogger(__name__)


class KnowledgeService:
    """CRUD + lookup API for the knowledge_entries table."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Queries ───────────────────────────────────────────────────────────

    async def list_by_category(
        self,
        category: str,
        *,
        country: str | None = None,
        include_global: bool = True,
    ) -> list[KnowledgeEntry]:
        """Return all entries in a category, optionally filtered by country.

        If `include_global` is True (default), rows with country=NULL are
        always included alongside country-specific rows.
        """
        conditions = [KnowledgeEntry.category == category]

        if country:
            if include_global:
                conditions.append(
                    (KnowledgeEntry.country == country)
                    | (KnowledgeEntry.country.is_(None))
                )
            else:
                conditions.append(KnowledgeEntry.country == country)

        stmt = (
            select(KnowledgeEntry)
            .where(and_(*conditions))
            .order_by(KnowledgeEntry.sort_order, KnowledgeEntry.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_code(self, category: str, code: str) -> KnowledgeEntry | None:
        """Fetch a single entry by category + code."""
        stmt = select(KnowledgeEntry).where(
            and_(
                KnowledgeEntry.category == category,
                KnowledgeEntry.code == code,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_regulatory_bodies(
        self, country: str | None = None
    ) -> dict[str, list[str]]:
        """Return {code: [aliases]} dict — drop-in replacement for the old
        REGULATORY_BODIES class constant."""
        entries = await self.list_by_category("regulatory_body", country=country)
        return {e.code: e.aliases for e in entries}

    async def get_sector_keywords(
        self, country: str | None = None
    ) -> dict[str, list[str]]:
        """Return {sector_code: [keywords]} dict — replaces old sector_keywords."""
        entries = await self.list_by_category("sector", country=country)
        return {e.code: e.keywords for e in entries}

    async def get_entity_type_keywords(
        self, country: str | None = None
    ) -> dict[str, list[str]]:
        """Return {entity_type: [keywords]} dict — replaces old entity_keywords."""
        entries = await self.list_by_category("entity_type", country=country)
        return {e.code: e.keywords for e in entries}

    async def get_domains(self, country: str | None = None) -> list[dict[str, Any]]:
        """Return list of domain definitions for frontend domain filters."""
        entries = await self.list_by_category("domain", country=country)
        return [
            {
                "id": str(e.id),
                "code": e.code,
                "name": e.name,
                "description": e.description,
                "metadata": e.metadata_,
                "sort_order": e.sort_order,
            }
            for e in entries
        ]

    # ── Mutations ─────────────────────────────────────────────────────────

    async def create(self, **kwargs: Any) -> KnowledgeEntry:
        """Create a new knowledge entry."""
        entry = KnowledgeEntry(**kwargs)
        self.db.add(entry)
        await self.db.flush()
        logger.info(f"Created knowledge entry: {entry.category}/{entry.code}")
        return entry

    async def update_entry(
        self, entry_id: UUID, **kwargs: Any
    ) -> KnowledgeEntry | None:
        """Update an existing knowledge entry."""
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
        result = await self.db.execute(stmt)
        entry = result.scalar_one_or_none()
        if not entry:
            return None

        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)

        await self.db.flush()
        logger.info(f"Updated knowledge entry: {entry.category}/{entry.code}")
        return entry

    async def delete_entry(self, entry_id: UUID) -> bool:
        """Hard-delete a knowledge entry."""
        stmt = delete(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
        result = await self.db.execute(stmt)
        return getattr(result, "rowcount", 0) > 0

    async def upsert(
        self,
        category: str,
        code: str,
        *,
        name: str,
        country: str | None = None,
        aliases: list[str] | None = None,
        keywords: list[str] | None = None,
        metadata_: dict | None = None,
        description: str | None = None,
        sort_order: int = 0,
        source: str = "seed",
        confidence: float = 1.0,
    ) -> KnowledgeEntry:
        """Insert or update by category+code (idempotent seed helper)."""
        existing = await self.get_by_code(category, code)
        if existing:
            existing.name = name
            existing.country = country
            existing.aliases = aliases or existing.aliases
            existing.keywords = keywords or existing.keywords
            existing.metadata_ = (
                metadata_ if metadata_ is not None else existing.metadata_
            )
            existing.description = description or existing.description
            existing.sort_order = sort_order
            existing.source = source
            existing.confidence = confidence
            await self.db.flush()
            return existing

        return await self.create(
            category=category,
            code=code,
            name=name,
            country=country,
            aliases=aliases or [],
            keywords=keywords or [],
            metadata_=metadata_ or {},
            description=description,
            sort_order=sort_order,
            source=source,
            confidence=confidence,
        )
