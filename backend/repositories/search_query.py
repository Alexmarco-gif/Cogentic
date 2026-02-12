"""Search Query repository"""

import time
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.search_query import SearchQuery
from backend.repositories.audit import audit_logger
from backend.repositories.base import TenantRepository


class SearchQueryRepository(TenantRepository[SearchQuery]):
    """Repository for Deep Live Search query operations.

    Search queries are tenant-scoped (org_id + user_id).
    Supports cache lookup via query_hash (SHA-256) for Redis 15min TTL.
    """

    def __init__(
        self,
        db: AsyncSession,
        org_id: UUID,
        user_id: UUID | None = None,
        request_id: str | None = None,
    ):
        super().__init__(SearchQuery, db, org_id, user_id, request_id)

    async def get_user_history(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[SearchQuery]:
        """Get a user's search history (most recent first)"""
        start_time = time.time()

        result = await self.db.execute(
            select(SearchQuery)
            .where(
                SearchQuery.user_id == user_id,
                SearchQuery.org_id == self.org_id,
            )
            .order_by(desc(SearchQuery.created_at))
            .offset(skip)
            .limit(limit)
        )
        records = list(result.scalars().all())

        duration_ms = (time.time() - start_time) * 1000
        audit_logger.log_query(
            user_id=self.user_id,
            org_id=self.org_id,
            table="search_queries",
            action="list_user_history",
            filters={"user_id": user_id},
            result_count=len(records),
            duration_ms=duration_ms,
            request_id=self.request_id,
        )
        return records

    async def find_by_hash(self, query_hash: str) -> SearchQuery | None:
        """Find a cached search result by query hash (SHA-256).

        Used to check if an identical query result exists in the DB
        before calling the AI synthesis engine.
        """
        result = await self.db.execute(
            select(SearchQuery)
            .where(
                SearchQuery.query_hash == query_hash,
                SearchQuery.org_id == self.org_id,
            )
            .order_by(desc(SearchQuery.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
