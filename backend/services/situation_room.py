"""Situation Room service.

Aggregates live signals, briefs, anomalies, and trends per industry
into a unified dashboard view. No new DB tables — reads from existing
signals, signal_scores, intelligence_briefs, and brief_signals tables.

Used by:
  - REST: GET /api/v1/situation-room/{industry}  (snapshot)
  - WebSocket: pushed via ConnectionManager on new signal events
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Float, case, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db_context
from backend.models.brief_signal import BriefSignal
from backend.models.industry import Industry
from backend.models.intelligence_brief import IntelligenceBrief
from backend.models.signal import Signal
from backend.models.signal_score import SignalScore
from backend.schemas.situation_room import (
    ActiveAlert,
    BriefSummary,
    DashboardMetrics,
    SituationRoomDashboard,
    SignalFeedItem,
    SignalPriority,
    SignalTypeBreakdown,
    TrendPoint,
)

logger = logging.getLogger(__name__)


def _classify_priority(confidence: float, is_anomaly: bool) -> SignalPriority:
    """Derive signal priority from confidence and anomaly status."""
    if is_anomaly and confidence >= 0.85:
        return SignalPriority.CRITICAL
    if confidence >= 0.85:
        return SignalPriority.HIGH
    if confidence >= 0.60:
        return SignalPriority.MEDIUM
    return SignalPriority.LOW


class SituationRoomService:
    """Builds live dashboard data by aggregating existing tables.

    All queries are scoped to a single industry and respect
    multi-tenancy (global signals + org-scoped signals where applicable).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Public API ───────────────────────────────────────────────────

    async def get_dashboard(
        self,
        industry_slug: str,
        *,
        org_id: UUID | None = None,
        signal_types: list[str] | None = None,
        min_confidence: float = 0.0,
        hours: int = 168,
        limit: int = 50,
    ) -> SituationRoomDashboard:
        """Build a complete dashboard snapshot for an industry.

        Args:
            industry_slug: Industry slug (e.g. "fintech", "ecommerce").
            org_id: Optional org scope (includes global + org signals).
            signal_types: Filter by type(s): news, social, regulatory, etc.
            min_confidence: Minimum confidence threshold.
            hours: Lookback window in hours.
            limit: Max signals in feed.

        Returns:
            SituationRoomDashboard with metrics, feed, alerts, briefs.

        Raises:
            ValueError: If industry_slug not found.
        """
        # Resolve industry
        industry = await self._get_industry(industry_slug)
        if not industry:
            raise ValueError(f"Industry not found: {industry_slug}")

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Run aggregations in parallel-ish (sequential awaits but each is a
        # single DB round-trip)
        metrics = await self._build_metrics(
            industry.id, org_id, cutoff, min_confidence
        )
        recent_signals = await self._get_recent_signals(
            industry.id, org_id, cutoff, signal_types, min_confidence, limit
        )
        alerts = await self._get_active_alerts(industry.id, org_id, cutoff)
        briefs = await self._get_published_briefs(industry.id, org_id)

        return SituationRoomDashboard(
            industry_id=industry.id,
            industry_name=industry.name,
            industry_slug=industry.slug,
            metrics=metrics,
            recent_signals=recent_signals,
            active_alerts=alerts,
            published_briefs=briefs,
            generated_at=datetime.now(timezone.utc),
        )

    async def get_signal_feed(
        self,
        industry_slug: str,
        *,
        org_id: UUID | None = None,
        since: datetime | None = None,
        limit: int = 20,
    ) -> list[SignalFeedItem]:
        """Get recent signals since a timestamp (for WebSocket delta pushes).

        Args:
            industry_slug: Industry slug.
            org_id: Optional org scope.
            since: Only signals created after this time.
            limit: Max count.

        Returns:
            List of SignalFeedItem ordered by fetched_at desc.
        """
        industry = await self._get_industry(industry_slug)
        if not industry:
            return []

        cutoff = since or (datetime.now(timezone.utc) - timedelta(hours=1))
        return await self._get_recent_signals(
            industry.id, org_id, cutoff, None, 0.0, limit
        )

    # ── Internal: Industry Lookup ────────────────────────────────────

    async def _get_industry(self, slug: str) -> Industry | None:
        """Resolve industry by slug."""
        stmt = select(Industry).where(Industry.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ── Internal: Metrics ────────────────────────────────────────────

    async def _build_metrics(
        self,
        industry_id: UUID,
        org_id: UUID | None,
        cutoff: datetime,
        min_confidence: float,
    ) -> DashboardMetrics:
        """Build aggregate dashboard metrics."""
        now = datetime.now(timezone.utc)
        cutoff_24h = now - timedelta(hours=24)
        cutoff_7d = now - timedelta(days=7)

        # Base filter: signals for this industry via their contract
        base_filter = self._signal_industry_filter(industry_id, org_id)

        # Total signals
        total_q = select(func.count(Signal.id)).where(
            *base_filter,
            Signal.confidence >= min_confidence,
        )
        total_signals = (await self.db.execute(total_q)).scalar() or 0

        # Signals last 24h
        q_24h = select(func.count(Signal.id)).where(
            *base_filter,
            Signal.fetched_at >= cutoff_24h,
        )
        signals_24h = (await self.db.execute(q_24h)).scalar() or 0

        # Signals last 7d
        q_7d = select(func.count(Signal.id)).where(
            *base_filter,
            Signal.fetched_at >= cutoff_7d,
        )
        signals_7d = (await self.db.execute(q_7d)).scalar() or 0

        # Average confidence
        avg_q = select(func.avg(Signal.confidence)).where(*base_filter)
        avg_conf = (await self.db.execute(avg_q)).scalar() or 0.0

        # Anomaly count (signals with anomaly score > 0.7)
        anomaly_q = (
            select(func.count(SignalScore.id))
            .join(Signal, Signal.id == SignalScore.signal_id)
            .where(
                *base_filter,
                SignalScore.score_type == "anomaly",
                SignalScore.score_value > 0.7,
                Signal.fetched_at >= cutoff,
            )
        )
        anomaly_count = (await self.db.execute(anomaly_q)).scalar() or 0

        # High priority count (confidence >= 0.85)
        high_q = select(func.count(Signal.id)).where(
            *base_filter,
            Signal.confidence >= 0.85,
            Signal.fetched_at >= cutoff,
        )
        high_priority = (await self.db.execute(high_q)).scalar() or 0

        # Active briefs
        briefs_q = select(func.count(IntelligenceBrief.id)).where(
            IntelligenceBrief.industry_id == industry_id,
            IntelligenceBrief.status == "published",
        )
        if org_id:
            briefs_q = briefs_q.where(
                (IntelligenceBrief.org_id == org_id)
                | (IntelligenceBrief.org_id.is_(None))
            )
        active_briefs = (await self.db.execute(briefs_q)).scalar() or 0

        # Type breakdown
        type_q = (
            select(
                Signal.signal_type,
                func.count(Signal.id).label("cnt"),
            )
            .where(*base_filter, Signal.fetched_at >= cutoff)
            .group_by(Signal.signal_type)
            .order_by(func.count(Signal.id).desc())
        )
        type_rows = (await self.db.execute(type_q)).all()
        type_total = sum(r.cnt for r in type_rows) or 1
        type_breakdown = [
            SignalTypeBreakdown(
                signal_type=r.signal_type,
                count=r.cnt,
                percentage=round(r.cnt / type_total * 100, 1),
            )
            for r in type_rows
        ]

        # Volume trend (last 14 days, daily buckets)
        volume_trend = await self._daily_trend(
            industry_id, org_id, days=14, metric="count"
        )

        # Confidence trend (last 14 days, daily average)
        confidence_trend = await self._daily_trend(
            industry_id, org_id, days=14, metric="avg_confidence"
        )

        return DashboardMetrics(
            total_signals=total_signals,
            signals_last_24h=signals_24h,
            signals_last_7d=signals_7d,
            avg_confidence=round(float(avg_conf), 3),
            anomaly_count=anomaly_count,
            high_priority_count=high_priority,
            active_briefs=active_briefs,
            type_breakdown=type_breakdown,
            signal_volume_trend=volume_trend,
            confidence_trend=confidence_trend,
        )

    # ── Internal: Signal Feed ────────────────────────────────────────

    async def _get_recent_signals(
        self,
        industry_id: UUID,
        org_id: UUID | None,
        cutoff: datetime,
        signal_types: list[str] | None,
        min_confidence: float,
        limit: int,
    ) -> list[SignalFeedItem]:
        """Fetch recent signals with their ML scores."""
        base_filter = self._signal_industry_filter(industry_id, org_id)

        # Subquery for anomaly scores
        anomaly_sub = (
            select(
                SignalScore.signal_id,
                SignalScore.score_value.label("anomaly_score"),
            )
            .where(SignalScore.score_type == "anomaly")
            .subquery()
        )

        # Subquery for trending scores
        trending_sub = (
            select(
                SignalScore.signal_id,
                SignalScore.score_value.label("trending_score"),
            )
            .where(SignalScore.score_type == "trending")
            .subquery()
        )

        stmt = (
            select(
                Signal,
                anomaly_sub.c.anomaly_score,
                trending_sub.c.trending_score,
            )
            .outerjoin(anomaly_sub, Signal.id == anomaly_sub.c.signal_id)
            .outerjoin(trending_sub, Signal.id == trending_sub.c.signal_id)
            .where(
                *base_filter,
                Signal.fetched_at >= cutoff,
                Signal.confidence >= min_confidence,
            )
            .order_by(Signal.fetched_at.desc())
            .limit(limit)
        )

        if signal_types:
            stmt = stmt.where(Signal.signal_type.in_(signal_types))

        rows = (await self.db.execute(stmt)).all()

        items: list[SignalFeedItem] = []
        for row in rows:
            signal = row[0]
            anomaly = row[1]
            trending = row[2]
            is_anomaly = anomaly is not None and anomaly > 0.7

            items.append(
                SignalFeedItem(
                    id=signal.id,
                    title=signal.title,
                    summary=signal.summary,
                    signal_type=signal.signal_type,
                    source_url=signal.source_url,
                    confidence=signal.confidence,
                    priority=_classify_priority(signal.confidence, is_anomaly),
                    published_at=signal.published_at,
                    fetched_at=signal.fetched_at,
                    is_anomaly=is_anomaly,
                    anomaly_score=anomaly,
                    trending_score=trending,
                    entity_names=[],  # Populated below if needed
                )
            )

        # Batch-load entity names for the feed items
        if items:
            await self._enrich_entity_names(items)

        return items

    async def _enrich_entity_names(self, items: list[SignalFeedItem]) -> None:
        """Attach entity display names to signal feed items."""
        from backend.models.entity import Entity
        from backend.models.signal_entity import SignalEntity

        signal_ids = [item.id for item in items]
        stmt = (
            select(SignalEntity.signal_id, Entity.name)
            .join(Entity, Entity.id == SignalEntity.entity_id)
            .where(SignalEntity.signal_id.in_(signal_ids))
        )
        rows = (await self.db.execute(stmt)).all()

        # Group by signal_id
        entity_map: dict[UUID, list[str]] = {}
        for signal_id, name in rows:
            entity_map.setdefault(signal_id, []).append(name)

        for item in items:
            item.entity_names = entity_map.get(item.id, [])

    # ── Internal: Alerts ─────────────────────────────────────────────

    async def _get_active_alerts(
        self,
        industry_id: UUID,
        org_id: UUID | None,
        cutoff: datetime,
    ) -> list[ActiveAlert]:
        """Get anomalies and high-confidence signals as alerts."""
        base_filter = self._signal_industry_filter(industry_id, org_id)

        # Anomaly-based alerts (anomaly score > 0.7)
        anomaly_stmt = (
            select(
                Signal.id,
                Signal.title,
                Signal.signal_type,
                Signal.confidence,
                SignalScore.score_value.label("anomaly_score"),
                Signal.fetched_at,
            )
            .join(SignalScore, Signal.id == SignalScore.signal_id)
            .where(
                *base_filter,
                SignalScore.score_type == "anomaly",
                SignalScore.score_value > 0.7,
                Signal.fetched_at >= cutoff,
            )
            .order_by(SignalScore.score_value.desc())
            .limit(20)
        )
        anomaly_rows = (await self.db.execute(anomaly_stmt)).all()

        alerts: list[ActiveAlert] = []
        for row in anomaly_rows:
            reason = "Anomaly detected"
            if row.confidence >= 0.85:
                reason = "Critical: High-confidence anomaly"
            elif row.anomaly_score > 0.9:
                reason = "Severe anomaly score"

            alerts.append(
                ActiveAlert(
                    signal_id=row.id,
                    title=row.title,
                    signal_type=row.signal_type,
                    confidence=row.confidence,
                    anomaly_score=row.anomaly_score,
                    reason=reason,
                    detected_at=row.fetched_at,
                )
            )

        return alerts

    # ── Internal: Briefs ─────────────────────────────────────────────

    async def _get_published_briefs(
        self,
        industry_id: UUID,
        org_id: UUID | None,
    ) -> list[BriefSummary]:
        """Get published briefs for the industry sidebar."""
        stmt = (
            select(IntelligenceBrief)
            .options(selectinload(IntelligenceBrief.signal_links))
            .where(
                IntelligenceBrief.industry_id == industry_id,
                IntelligenceBrief.status == "published",
            )
            .order_by(IntelligenceBrief.refreshed_at.desc().nullslast())
            .limit(10)
        )
        if org_id:
            stmt = stmt.where(
                (IntelligenceBrief.org_id == org_id)
                | (IntelligenceBrief.org_id.is_(None))
            )

        result = await self.db.execute(stmt)
        briefs = result.scalars().all()

        return [
            BriefSummary(
                id=b.id,
                title=b.title,
                bluf=b.bluf,
                status=b.status,
                refreshed_at=b.refreshed_at,
                signal_count=len(b.signal_links),
            )
            for b in briefs
        ]

    # ── Internal: Daily Trend ────────────────────────────────────────

    async def _daily_trend(
        self,
        industry_id: UUID,
        org_id: UUID | None,
        *,
        days: int = 14,
        metric: str = "count",
    ) -> list[TrendPoint]:
        """Build a daily time-series for signal volume or avg confidence.

        Args:
            industry_id: Target industry.
            org_id: Optional org scope.
            days: Number of days to look back.
            metric: "count" or "avg_confidence".

        Returns:
            List of TrendPoint, one per day, ordered chronologically.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        base_filter = self._signal_industry_filter(industry_id, org_id)

        date_trunc = func.date_trunc("day", Signal.fetched_at)

        if metric == "avg_confidence":
            value_col = func.avg(Signal.confidence)
        else:
            value_col = cast(func.count(Signal.id), Float)

        stmt = (
            select(date_trunc.label("day"), value_col.label("val"))
            .where(*base_filter, Signal.fetched_at >= cutoff)
            .group_by("day")
            .order_by("day")
        )

        rows = (await self.db.execute(stmt)).all()
        return [
            TrendPoint(timestamp=row.day, value=round(float(row.val), 3))
            for row in rows
        ]

    # ── Internal: Helpers ────────────────────────────────────────────

    def _signal_industry_filter(
        self, industry_id: UUID, org_id: UUID | None
    ) -> list:
        """Build common WHERE clauses for industry-scoped signal queries.

        Signals are connected to industries via their signal_contract.
        We join Signal → SignalContract and filter by contract.industry_id.
        Also applies org scoping (global + org-specific).
        """
        from backend.models.signal_contract import SignalContract

        filters = [
            Signal.contract_id == SignalContract.id,
            SignalContract.industry_id == industry_id,
        ]

        if org_id:
            filters.append(
                (Signal.org_id == org_id) | (Signal.org_id.is_(None))
            )

        return filters


# ── Convenience Factory ──────────────────────────────────────────────


async def get_situation_room_service() -> SituationRoomService:
    """Create a SituationRoomService with a fresh DB session.

    Usage:
        service = await get_situation_room_service()
        dashboard = await service.get_dashboard("fintech")
    """
    async with get_db_context() as db:
        return SituationRoomService(db)
