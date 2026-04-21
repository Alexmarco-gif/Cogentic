"""Market Data API — time-series price/rate data extracted from signals.

Provides endpoints for querying market data points extracted by NER:
  - Price trends by metric (e.g. rice price over time)
  - Per-entity data (e.g. all data points linked to "Dangote Cement")
  - Per-country aggregations
  - Latest values for a set of metrics
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.middleware.feature_gating import require_feature
from backend.models.market_data import MarketDataPoint

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/market-data")


# ── Response Schemas ─────────────────────────────────────────────────────────


class MarketDataPointResponse(BaseModel):
    """A single market data point."""

    id: str
    metric: str
    value: float
    unit: str
    currency: str | None
    observed_at: datetime
    signal_id: str | None
    entity_id: str | None
    country_code: str | None
    region: str | None
    context: str | None
    confidence: float
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_instance(cls, obj: MarketDataPoint) -> "MarketDataPointResponse":
        return cls(
            id=str(obj.id),
            metric=obj.metric,
            value=obj.value,
            unit=obj.unit,
            currency=obj.currency,
            observed_at=obj.observed_at,
            signal_id=str(obj.signal_id) if obj.signal_id else None,
            entity_id=str(obj.entity_id) if obj.entity_id else None,
            country_code=obj.country_code,
            region=obj.region,
            context=obj.context,
            confidence=obj.confidence,
            created_at=obj.created_at,
        )


class MarketDataListResponse(BaseModel):
    """Paginated list of market data points."""

    items: list[MarketDataPointResponse]
    total: int
    skip: int
    limit: int


class MetricSummary(BaseModel):
    """Summary statistics for a single metric."""

    metric: str
    count: int
    latest_value: float | None
    latest_observed_at: datetime | None
    min_value: float | None
    max_value: float | None
    avg_value: float | None
    unit: str | None
    currency: str | None


class MarketDataStatsResponse(BaseModel):
    """Aggregated stats across all market data."""

    total_points: int
    unique_metrics: int
    countries_covered: int
    metrics: list[MetricSummary]


class LatestValueResponse(BaseModel):
    """Latest value for a specific metric."""

    metric: str
    value: float
    unit: str
    currency: str | None
    observed_at: datetime
    country_code: str | None
    signal_id: str | None


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("", response_model=MarketDataListResponse)
async def list_market_data(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _feature_check: bool = Depends(require_feature("market_data")),
    metric: str | None = Query(None, description="Filter by metric name"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
    country_code: str | None = Query(
        None, max_length=3, description="ISO 3166 alpha-3"
    ),
    since: datetime | None = Query(None, description="Only points after this datetime"),
    until: datetime | None = Query(
        None, description="Only points before this datetime"
    ),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """List market data points with filtering.

    Supports filtering by metric, entity, country, time range, and confidence.
    Results are ordered by observed_at descending (newest first).
    """
    query = select(MarketDataPoint)
    count_query = select(func.count(MarketDataPoint.id))

    if metric:
        query = query.where(MarketDataPoint.metric == metric)
        count_query = count_query.where(MarketDataPoint.metric == metric)
    if entity_id:
        query = query.where(MarketDataPoint.entity_id == entity_id)
        count_query = count_query.where(MarketDataPoint.entity_id == entity_id)
    if country_code:
        query = query.where(MarketDataPoint.country_code == country_code)
        count_query = count_query.where(MarketDataPoint.country_code == country_code)
    if since:
        query = query.where(MarketDataPoint.observed_at >= since)
        count_query = count_query.where(MarketDataPoint.observed_at >= since)
    if until:
        query = query.where(MarketDataPoint.observed_at <= until)
        count_query = count_query.where(MarketDataPoint.observed_at <= until)
    if min_confidence > 0:
        query = query.where(MarketDataPoint.confidence >= min_confidence)
        count_query = count_query.where(MarketDataPoint.confidence >= min_confidence)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(MarketDataPoint.observed_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    points = result.scalars().all()

    return MarketDataListResponse(
        items=[MarketDataPointResponse.from_orm_instance(p) for p in points],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=MarketDataStatsResponse)
async def get_market_data_stats(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _feature_check: bool = Depends(require_feature("market_data")),
    country_code: str | None = Query(None, max_length=3),
):
    """Get aggregated statistics across all market data.

    Returns total points, unique metrics, and per-metric summaries
    including latest value, min/max/avg.
    """
    base_filter = []
    if country_code:
        base_filter.append(MarketDataPoint.country_code == country_code)

    # Total count
    total_q = select(func.count(MarketDataPoint.id))
    if base_filter:
        total_q = total_q.where(*base_filter)
    total = (await db.execute(total_q)).scalar() or 0

    # Unique metrics
    metrics_q = select(func.count(func.distinct(MarketDataPoint.metric)))
    if base_filter:
        metrics_q = metrics_q.where(*base_filter)
    unique_metrics = (await db.execute(metrics_q)).scalar() or 0

    # Countries covered
    countries_q = select(func.count(func.distinct(MarketDataPoint.country_code)))
    if base_filter:
        countries_q = countries_q.where(*base_filter)
    countries = (await db.execute(countries_q)).scalar() or 0

    # Per-metric summaries (top 50 by count)
    summary_q = (
        select(
            MarketDataPoint.metric,
            func.count(MarketDataPoint.id).label("count"),
            func.min(MarketDataPoint.value).label("min_value"),
            func.max(MarketDataPoint.value).label("max_value"),
            func.avg(MarketDataPoint.value).label("avg_value"),
        )
        .group_by(MarketDataPoint.metric)
        .order_by(func.count(MarketDataPoint.id).desc())
        .limit(50)
    )
    if base_filter:
        summary_q = summary_q.where(*base_filter)

    summary_result = await db.execute(summary_q)
    summaries = summary_result.all()

    # For each metric, get the latest value
    metric_summaries = []
    for row in summaries:
        # Get the latest data point for this metric
        latest_q = (
            select(MarketDataPoint)
            .where(MarketDataPoint.metric == row.metric)
            .order_by(MarketDataPoint.observed_at.desc())
            .limit(1)
        )
        if base_filter:
            latest_q = latest_q.where(*base_filter)

        latest_result = await db.execute(latest_q)
        latest = latest_result.scalar_one_or_none()

        metric_summaries.append(
            MetricSummary(
                metric=row.metric,
                count=row.count,
                latest_value=latest.value if latest else None,
                latest_observed_at=latest.observed_at if latest else None,
                min_value=round(row.min_value, 4)
                if row.min_value is not None
                else None,
                max_value=round(row.max_value, 4)
                if row.max_value is not None
                else None,
                avg_value=round(float(row.avg_value), 4)
                if row.avg_value is not None
                else None,
                unit=latest.unit if latest else None,
                currency=latest.currency if latest else None,
            )
        )

    return MarketDataStatsResponse(
        total_points=total,
        unique_metrics=unique_metrics,
        countries_covered=countries,
        metrics=metric_summaries,
    )


@router.get("/latest", response_model=list[LatestValueResponse])
async def get_latest_values(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _feature_check: bool = Depends(require_feature("market_data")),
    metrics: str = Query(..., description="Comma-separated metric names"),
    country_code: str | None = Query(None, max_length=3),
):
    """Get the latest value for each requested metric.

    Useful for dashboard widgets that show current prices/rates.
    """
    metric_list = [m.strip() for m in metrics.split(",") if m.strip()]
    if not metric_list:
        return []

    results = []
    for metric_name in metric_list[:20]:  # Cap at 20 metrics per request
        query = (
            select(MarketDataPoint)
            .where(MarketDataPoint.metric == metric_name)
            .order_by(MarketDataPoint.observed_at.desc())
            .limit(1)
        )
        if country_code:
            query = query.where(MarketDataPoint.country_code == country_code)

        result = await db.execute(query)
        point = result.scalar_one_or_none()

        if point:
            results.append(
                LatestValueResponse(
                    metric=point.metric,
                    value=point.value,
                    unit=point.unit,
                    currency=point.currency,
                    observed_at=point.observed_at,
                    country_code=point.country_code,
                    signal_id=str(point.signal_id) if point.signal_id else None,
                )
            )

    return results


@router.get("/trend/{metric}", response_model=MarketDataListResponse)
async def get_metric_trend(
    metric: str,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _feature_check: bool = Depends(require_feature("market_data")),
    entity_id: UUID | None = Query(None),
    country_code: str | None = Query(None, max_length=3),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get historical trend data for a specific metric.

    Returns data points ordered chronologically (oldest first) for charting.
    """
    from datetime import timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = select(MarketDataPoint).where(
        MarketDataPoint.metric == metric,
        MarketDataPoint.observed_at >= since,
    )
    count_query = select(func.count(MarketDataPoint.id)).where(
        MarketDataPoint.metric == metric,
        MarketDataPoint.observed_at >= since,
    )

    if entity_id:
        query = query.where(MarketDataPoint.entity_id == entity_id)
        count_query = count_query.where(MarketDataPoint.entity_id == entity_id)
    if country_code:
        query = query.where(MarketDataPoint.country_code == country_code)
        count_query = count_query.where(MarketDataPoint.country_code == country_code)

    total = (await db.execute(count_query)).scalar() or 0

    # Chronological order for charting
    query = query.order_by(MarketDataPoint.observed_at.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    points = result.scalars().all()

    return MarketDataListResponse(
        items=[MarketDataPointResponse.from_orm_instance(p) for p in points],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/metrics", response_model=list[str])
async def list_available_metrics(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _feature_check: bool = Depends(require_feature("market_data")),
    country_code: str | None = Query(None, max_length=3),
):
    """List all distinct metric names in the system.

    Useful for populating metric selector dropdowns.
    """
    query = select(func.distinct(MarketDataPoint.metric)).order_by(
        MarketDataPoint.metric
    )
    if country_code:
        query = query.where(MarketDataPoint.country_code == country_code)

    result = await db.execute(query)
    return [row[0] for row in result.all()]
