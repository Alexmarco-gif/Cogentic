"""Signal repository"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.signal import Signal
from backend.models.signal_entity import SignalEntity
from backend.repositories.base import BaseRepository


class SignalRepository(BaseRepository[Signal]):
    """Repository for signal operations.

    Signals are globally accessible (not tenant-scoped).
    org_id on a signal is optional — NULL means global, set means org-specific.
    Confidence thresholds: >= 0.85 (brief-eligible), >= 0.60 (visible), < 0.60 (flagged).
    """

    def __init__(self, db: AsyncSession):
        super().__init__(Signal, db)

    async def get_by_contract(
        self,
        contract_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Signal]:
        """Get signals from a specific contract"""
        result = await self.db.execute(
            select(Signal)
            .where(Signal.contract_id == contract_id)
            .order_by(desc(Signal.fetched_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_type(
        self,
        signal_type: str,
        *,
        min_confidence: float = 0.6,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Signal]:
        """Get signals by type (news, social, regulatory, etc.) above min confidence"""
        result = await self.db.execute(
            select(Signal)
            .where(
                Signal.signal_type == signal_type,
                Signal.confidence >= min_confidence,
            )
            .order_by(desc(Signal.published_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_brief_eligible(
        self,
        *,
        contract_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Signal]:
        """Get signals with confidence >= 0.85 (eligible for intelligence briefs)"""
        query = select(Signal).where(Signal.confidence >= 0.85)
        if contract_id:
            query = query.where(Signal.contract_id == contract_id)
        result = await self.db.execute(
            query.order_by(desc(Signal.published_at)).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_visible(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Signal]:
        """Get signals with confidence >= 0.6 (visible in catalog)"""
        result = await self.db.execute(
            select(Signal)
            .where(Signal.confidence >= 0.6)
            .order_by(desc(Signal.published_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_by_content_hash(self, content_hash: str) -> Signal | None:
        """Find a signal by content hash (SHA-256) for deduplication"""
        result = await self.db.execute(
            select(Signal).where(Signal.content_hash == content_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_entity(
        self,
        entity_id: UUID,
        *,
        min_confidence: float = 0.6,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Signal]:
        """Get all signals linked to a given entity"""
        result = await self.db.execute(
            select(Signal)
            .join(SignalEntity, Signal.id == SignalEntity.signal_id)
            .where(
                SignalEntity.entity_id == entity_id,
                Signal.confidence >= min_confidence,
            )
            .order_by(desc(Signal.published_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_trending(
        self,
        *,
        limit: int = 20,
    ) -> list[Signal]:
        """Get trending signals (high confidence, recently published).

        Simple heuristic for MVP — will be replaced by ML trending_scorer.
        """
        result = await self.db.execute(
            select(Signal)
            .where(
                Signal.confidence >= 0.7,
                Signal.published_at.is_not(None),
            )
            .order_by(desc(Signal.published_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_contract(self, contract_id: UUID) -> int:
        """Count signals for a given contract"""
        result = await self.db.execute(
            select(func.count(Signal.id)).where(Signal.contract_id == contract_id)
        )
        return result.scalar_one()

    async def get_expired(self, before: datetime) -> list[Signal]:
        """Get signals past their expiration date (for 90-day retention archival)"""
        result = await self.db.execute(
            select(Signal).where(
                Signal.expires_at.is_not(None),
                Signal.expires_at < before,
            )
        )
        return list(result.scalars().all())

    async def get_feed(
        self,
        *,
        industry_id: UUID | None = None,
        signal_type: str | None = None,
        min_confidence: float = 0.6,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Signal]:
        """Get real-time signal feed (paginated, filterable).

        Supports filtering by industry (via contract) and signal type.
        """
        query = select(Signal).where(Signal.confidence >= min_confidence)

        if signal_type:
            query = query.where(Signal.signal_type == signal_type)

        if industry_id:
            from backend.models.signal_contract import SignalContract

            query = query.join(
                SignalContract, Signal.contract_id == SignalContract.id
            ).where(SignalContract.industry_id == industry_id)

        result = await self.db.execute(
            query.order_by(desc(Signal.fetched_at)).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
