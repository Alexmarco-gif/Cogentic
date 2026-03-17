"""ML Model Run repository"""

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.ml_model_run import MLModelRun
from backend.repositories.base import BaseRepository


class MLModelRunRepository(BaseRepository[MLModelRun]):
    """Repository for ML pipeline audit trail.

    ML model runs are global (not tenant-scoped).
    Day-1 models: anomaly_detector, trending_scorer, confidence_calibrator.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(MLModelRun, db)

    async def get_by_model(
        self,
        model_name: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[MLModelRun]:
        """Get runs for a specific model (most recent first)"""
        result = await self.db.execute(
            select(MLModelRun)
            .where(MLModelRun.model_name == model_name)
            .order_by(desc(MLModelRun.ran_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_run(
        self,
        model_name: str,
    ) -> MLModelRun | None:
        """Get the most recent run for a model"""
        result = await self.db.execute(
            select(MLModelRun)
            .where(
                MLModelRun.model_name == model_name,
                MLModelRun.status == "completed",
            )
            .order_by(desc(MLModelRun.ran_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_failed_runs(
        self,
        *,
        model_name: str | None = None,
        limit: int = 20,
    ) -> list[MLModelRun]:
        """Get recent failed runs for monitoring"""
        query = select(MLModelRun).where(MLModelRun.status == "failed")
        if model_name:
            query = query.where(MLModelRun.model_name == model_name)
        result = await self.db.execute(
            query.order_by(desc(MLModelRun.ran_at)).limit(limit)
        )
        return list(result.scalars().all())
