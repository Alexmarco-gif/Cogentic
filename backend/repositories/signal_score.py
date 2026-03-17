"""Signal Score repository"""

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.signal_score import SignalScore
from backend.repositories.base import BaseRepository


class SignalScoreRepository(BaseRepository[SignalScore]):
    """Repository for ML-computed signal scores.

    Signal scores are global (not tenant-scoped).
    Score types: anomaly, trending, confidence.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(SignalScore, db)

    async def get_by_signal(
        self,
        signal_id: UUID,
    ) -> list[SignalScore]:
        """Get all scores for a signal"""
        result = await self.db.execute(
            select(SignalScore)
            .where(SignalScore.signal_id == signal_id)
            .order_by(SignalScore.score_type)
        )
        return list(result.scalars().all())

    async def get_by_signal_and_type(
        self,
        signal_id: UUID,
        score_type: str,
    ) -> SignalScore | None:
        """Get a specific score type for a signal"""
        result = await self.db.execute(
            select(SignalScore)
            .where(
                SignalScore.signal_id == signal_id,
                SignalScore.score_type == score_type,
            )
            .order_by(desc(SignalScore.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_model_run(
        self,
        model_run_id: UUID,
    ) -> list[SignalScore]:
        """Get all scores produced by a specific model run"""
        result = await self.db.execute(
            select(SignalScore)
            .where(SignalScore.model_run_id == model_run_id)
            .order_by(SignalScore.signal_id)
        )
        return list(result.scalars().all())

    async def upsert_score(
        self,
        signal_id: UUID,
        score_type: str,
        score_value: float,
        model_run_id: UUID | None = None,
    ) -> SignalScore:
        """Create or update a score for a signal.

        If a score of the same type already exists for this signal,
        update it. Otherwise create a new one.
        """
        existing = await self.get_by_signal_and_type(signal_id, score_type)
        if existing:
            existing.score_value = score_value
            if model_run_id:
                existing.model_run_id = model_run_id
            await self.db.flush()
            await self.db.refresh(existing)
            return existing

        return await self.create(
            signal_id=signal_id,
            score_type=score_type,
            score_value=score_value,
            model_run_id=model_run_id,
        )
