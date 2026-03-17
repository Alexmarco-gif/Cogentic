"""Intelligence Brief repository"""

import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.intelligence_brief import IntelligenceBrief
from backend.repositories.audit import audit_logger
from backend.repositories.base import TenantRepository


class IntelligenceBriefRepository(TenantRepository[IntelligenceBrief]):
    """Repository for intelligence brief operations.

    Briefs are org-scoped (org_id=NULL for global/template briefs,
    org_id set for org-specific customizations).

    Uses TenantRepository for org isolation — queries automatically
    include both global (org_id=NULL) and org-specific briefs.
    """

    def __init__(
        self,
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID | None = None,
        request_id: str | None = None,
    ):
        super().__init__(IntelligenceBrief, db, org_id, user_id, request_id)

    async def get_published(
        self,
        *,
        industry_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[IntelligenceBrief]:
        """Get published briefs (global + org-specific) with optional industry filter.

        Returns both global (org_id=NULL) AND org-specific briefs.
        """
        start_time = time.time()

        query = select(IntelligenceBrief).where(
            IntelligenceBrief.status == "published",
            IntelligenceBrief.deleted_at.is_(None),
            (
                IntelligenceBrief.org_id.is_(None)
                | (IntelligenceBrief.org_id == self.org_id)
            ),
        )
        if industry_id:
            query = query.where(IntelligenceBrief.industry_id == industry_id)

        result = await self.db.execute(
            query.order_by(desc(IntelligenceBrief.refreshed_at))
            .offset(skip)
            .limit(limit)
        )
        records = list(result.scalars().all())

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=self.org_id,
            table="intelligence_briefs",
            action="list_published",
            filters={"industry_id": industry_id},
            result_count=len(records),
            duration_ms=duration_ms,
            request_id=self.request_id,
        )
        return records

    async def count_published(
        self,
        *,
        industry_id: UUID | None = None,
    ) -> int:
        """Count published briefs (global + org-specific) matching the same filters as get_published."""
        query = select(func.count(IntelligenceBrief.id)).where(
            IntelligenceBrief.status == "published",
            IntelligenceBrief.deleted_at.is_(None),
            (
                IntelligenceBrief.org_id.is_(None)
                | (IntelligenceBrief.org_id == self.org_id)
            ),
        )
        if industry_id:
            query = query.where(IntelligenceBrief.industry_id == industry_id)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_by_industry(
        self,
        industry_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[IntelligenceBrief]:
        """Get all briefs for an industry (global + org-scoped)"""
        result = await self.db.execute(
            select(IntelligenceBrief)
            .where(
                IntelligenceBrief.industry_id == industry_id,
                IntelligenceBrief.deleted_at.is_(None),
                (
                    IntelligenceBrief.org_id.is_(None)
                    | (IntelligenceBrief.org_id == self.org_id)
                ),
            )
            .order_by(desc(IntelligenceBrief.updated_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_with_signals(self, brief_id: UUID) -> IntelligenceBrief | None:
        """Get a brief with its linked signals pre-loaded"""
        result = await self.db.execute(
            select(IntelligenceBrief)
            .options(selectinload(IntelligenceBrief.signal_links))
            .where(
                IntelligenceBrief.id == brief_id,
                IntelligenceBrief.deleted_at.is_(None),
                (
                    IntelligenceBrief.org_id.is_(None)
                    | (IntelligenceBrief.org_id == self.org_id)
                ),
            )
        )
        return result.scalar_one_or_none()

    async def get_stale_briefs(
        self,
        stale_before: datetime,
    ) -> list[IntelligenceBrief]:
        """Get published briefs not refreshed since `stale_before`.

        Used by the brief refresh scheduler.
        """
        result = await self.db.execute(
            select(IntelligenceBrief).where(
                IntelligenceBrief.status == "published",
                IntelligenceBrief.deleted_at.is_(None),
                (
                    IntelligenceBrief.refreshed_at.is_(None)
                    | (IntelligenceBrief.refreshed_at < stale_before)
                ),
            )
        )
        return list(result.scalars().all())

    async def mark_refreshed(self, brief_id: UUID) -> IntelligenceBrief | None:
        """Update the refreshed_at timestamp after brief regeneration"""
        return await self.update(brief_id, refreshed_at=datetime.now(timezone.utc))
