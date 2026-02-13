"""Recommendation repository"""

from uuid import UUID

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.recommendation import Recommendation
from backend.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    """Repository for recommendation operations.

    Recommendations are not tenant-scoped (they link signals/briefs/entities
    by polymorphic source/target). Access control is handled at the service layer.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Recommendation, db)

    async def get_for_source(
        self,
        source_type: str,
        source_id: UUID,
        *,
        target_type: str | None = None,
        min_score: float = 0.0,
        limit: int = 10,
    ) -> list[Recommendation]:
        """Get recommendations for a source (e.g., related signals for a signal).

        Args:
            source_type: 'signal', 'brief', or 'entity'.
            source_id: Source record UUID.
            target_type: Optional filter for target type.
            min_score: Minimum recommendation score.
            limit: Max recommendations to return.
        """
        query = select(Recommendation).where(
            Recommendation.source_type == source_type,
            Recommendation.source_id == source_id,
            Recommendation.score >= min_score,
        )
        if target_type:
            query = query.where(Recommendation.target_type == target_type)

        result = await self.db.execute(
            query.order_by(desc(Recommendation.score)).limit(limit)
        )
        return list(result.scalars().all())

    async def upsert(
        self,
        *,
        source_type: str,
        source_id: UUID,
        target_type: str,
        target_id: UUID,
        score: float,
        reason: str | None = None,
        algorithm_version: str | None = None,
    ) -> Recommendation:
        """Create or update a recommendation."""
        # Check for existing
        result = await self.db.execute(
            select(Recommendation).where(
                Recommendation.source_type == source_type,
                Recommendation.source_id == source_id,
                Recommendation.target_type == target_type,
                Recommendation.target_id == target_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.score = score
            existing.reason = reason
            existing.algorithm_version = algorithm_version
            await self.db.flush()
            return existing

        rec = Recommendation(
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            score=score,
            reason=reason,
            algorithm_version=algorithm_version,
        )
        self.db.add(rec)
        await self.db.flush()
        return rec

    async def delete_for_source(
        self,
        source_type: str,
        source_id: UUID,
    ) -> int:
        """Delete all recommendations for a source (before regeneration)."""
        result = await self.db.execute(
            delete(Recommendation).where(
                Recommendation.source_type == source_type,
                Recommendation.source_id == source_id,
            )
        )
        await self.db.flush()
        return result.rowcount

    async def get_active(
        self,
        *,
        source_type: str | None = None,
        min_score: float = 0.5,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Recommendation]:
        """Get active recommendations above score threshold."""
        query = select(Recommendation).where(
            Recommendation.score >= min_score,
        )
        if source_type:
            query = query.where(Recommendation.source_type == source_type)

        result = await self.db.execute(
            query.order_by(desc(Recommendation.score)).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
