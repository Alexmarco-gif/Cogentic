"""ML Model Registry repository"""

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.ml_model_registry import MLModelRegistry
from backend.repositories.base import BaseRepository


class MLModelRegistryRepository(BaseRepository[MLModelRegistry]):
    """Repository for ML model version tracking.

    Manages the lifecycle of trained model artifacts.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(MLModelRegistry, db)

    async def get_active_version(
        self,
        model_name: str,
    ) -> MLModelRegistry | None:
        """Get the currently active version of a model."""
        result = await self.db.execute(
            select(MLModelRegistry)
            .where(
                MLModelRegistry.model_name == model_name,
                MLModelRegistry.status == "active",
            )
            .order_by(desc(MLModelRegistry.trained_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_versions(
        self,
        model_name: str,
        *,
        limit: int = 10,
    ) -> list[MLModelRegistry]:
        """Get all versions of a model (most recent first)."""
        result = await self.db.execute(
            select(MLModelRegistry)
            .where(MLModelRegistry.model_name == model_name)
            .order_by(desc(MLModelRegistry.trained_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def archive_old_versions(
        self,
        model_name: str,
        keep: int = 3,
    ) -> int:
        """Archive all but the latest N active versions.

        Returns the number of versions archived.
        """
        versions = await self.get_versions(model_name, limit=100)
        active_versions = [v for v in versions if v.status == "active"]

        archived = 0
        for v in active_versions[keep:]:
            v.status = "archived"
            archived += 1

        if archived > 0:
            await self.db.flush()

        return archived

    async def register_model(
        self,
        model_name: str,
        model_version: str,
        artifact_path: str,
        metrics: dict | None = None,
        training_samples: int | None = None,
        training_duration_ms: int | None = None,
        artifact_size_bytes: int | None = None,
    ) -> MLModelRegistry:
        """Register a new model version and set it as active."""
        from datetime import datetime, timezone

        entry = await self.create(
            model_name=model_name,
            model_version=model_version,
            artifact_path=artifact_path,
            metrics=metrics or {},
            status="active",
            training_samples=training_samples,
            training_duration_ms=training_duration_ms,
            artifact_size_bytes=artifact_size_bytes,
            trained_at=datetime.now(timezone.utc),
        )

        # Archive old versions beyond limit
        await self.archive_old_versions(model_name, keep=3)

        return entry
