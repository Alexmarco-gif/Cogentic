"""Repository for regulatory knowledge data access.

Extracts all direct ORM access from regulatory route handlers
into a proper repository layer following the project's BaseRepository pattern.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.regulatory_knowledge import (
    RegulatoryEvent,
    RegulatoryImpact,
    RegulatoryPattern,
    RegulatoryRule,
)


class RegulatoryRepository:
    """Repository for CRUD operations on regulatory knowledge models."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Events ────────────────────────────────────────────────────

    async def create_event(self, **kwargs) -> RegulatoryEvent:
        """Create a new regulatory event."""
        event = RegulatoryEvent(id=uuid4(), **kwargs)
        self.db.add(event)
        return event

    async def get_event(self, event_id: UUID) -> RegulatoryEvent | None:
        return await self.db.get(RegulatoryEvent, event_id)

    async def list_events(
        self,
        *,
        issuing_body: str | None = None,
        event_type: str | None = None,
        sector: str | None = None,
        verified_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> list[RegulatoryEvent]:
        filters = []
        if issuing_body:
            filters.append(RegulatoryEvent.issuing_body == issuing_body)
        if event_type:
            filters.append(RegulatoryEvent.event_type == event_type)
        if sector:
            filters.append(RegulatoryEvent.affected_sectors.contains([sector]))
        if verified_only:
            filters.append(RegulatoryEvent.verified_by_expert == True)  # noqa: E712

        query = (
            select(RegulatoryEvent)
            .where(and_(*filters) if filters else True)
            .order_by(desc(RegulatoryEvent.announced_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ── Rules ─────────────────────────────────────────────────────

    async def create_rule(self, **kwargs) -> RegulatoryRule:
        """Create a new regulatory rule."""
        rule = RegulatoryRule(id=uuid4(), **kwargs)
        self.db.add(rule)
        return rule

    # ── Patterns ──────────────────────────────────────────────────

    async def list_patterns(
        self,
        *,
        pattern_type: str | None = None,
        min_confidence: float = 0.5,
        skip: int = 0,
        limit: int = 50,
    ) -> list[RegulatoryPattern]:
        filters = [RegulatoryPattern.confidence_score >= min_confidence]
        if pattern_type:
            filters.append(RegulatoryPattern.pattern_type == pattern_type)

        query = (
            select(RegulatoryPattern)
            .where(and_(*filters))
            .order_by(RegulatoryPattern.confidence_score.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ── Stats ─────────────────────────────────────────────────────

    async def get_stats(self) -> dict:
        """Get aggregate statistics about the regulatory knowledge base."""
        events_by_body = await self.db.execute(
            select(
                RegulatoryEvent.issuing_body,
                func.count(RegulatoryEvent.id).label("count"),
            ).group_by(RegulatoryEvent.issuing_body)
        )

        verified_count = await self.db.execute(
            select(func.count(RegulatoryEvent.id)).where(
                RegulatoryEvent.verified_by_expert == True  # noqa: E712
            )
        )
        total_events = await self.db.execute(select(func.count(RegulatoryEvent.id)))
        total_rules = await self.db.execute(
            select(func.count(RegulatoryRule.id)).where(
                RegulatoryRule.is_active == True  # noqa: E712
            )
        )
        total_impacts = await self.db.execute(select(func.count(RegulatoryImpact.id)))

        # knowledge_base_age_days — days since the earliest recorded event
        first_event_result = await self.db.execute(
            select(func.min(RegulatoryEvent.announced_at))
        )
        first_event_date = first_event_result.scalar_one_or_none()
        if first_event_date:
            aware_first = first_event_date.replace(tzinfo=timezone.utc) if first_event_date.tzinfo is None else first_event_date
            knowledge_base_age_days = (datetime.now(timezone.utc) - aware_first).days
        else:
            knowledge_base_age_days = 0

        # learning_velocity — compare events added in last 30 days vs prior 30 days
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        recent_count_result = await self.db.execute(
            select(func.count(RegulatoryEvent.id)).where(
                RegulatoryEvent.created_at >= thirty_days_ago
            )
        )
        prior_count_result = await self.db.execute(
            select(func.count(RegulatoryEvent.id)).where(
                RegulatoryEvent.created_at >= sixty_days_ago,
                RegulatoryEvent.created_at < thirty_days_ago,
            )
        )
        recent_count = recent_count_result.scalar_one()
        prior_count = prior_count_result.scalar_one()

        if recent_count > prior_count:
            learning_velocity = "Growing"
        elif recent_count < prior_count:
            learning_velocity = "Declining"
        else:
            learning_velocity = "Stable"

        return {
            "total_events": total_events.scalar_one(),
            "verified_events": verified_count.scalar_one(),
            "active_rules": total_rules.scalar_one(),
            "recorded_impacts": total_impacts.scalar_one(),
            "events_by_regulator": [
                {"regulator": row[0], "count": row[1]} for row in events_by_body
            ],
            "knowledge_base_age_days": knowledge_base_age_days,
            "learning_velocity": learning_velocity,
        }
