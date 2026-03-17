"""Signal Alerts API — list, acknowledge, and summarise change-detection alerts."""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.models.signal_alert import SignalAlert

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts")


# ── Response schemas ──────────────────────────────────────────────────────────


class AlertResponse(BaseModel):
    id: str
    alert_type: str
    severity: str
    metric: str | None
    country_code: str | None
    title: str
    description: str | None
    current_value: float | None
    baseline_value: float | None
    deviation_pct: float | None
    acknowledged: bool
    acknowledged_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    unacknowledged: int


class AlertSummaryResponse(BaseModel):
    total: int
    unacknowledged: int
    by_severity: dict[str, int]
    by_metric: dict[str, int]


class AcknowledgeResponse(BaseModel):
    id: str
    acknowledged: bool
    acknowledged_at: datetime


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    severity: str | None = Query(None, pattern=r"^(low|medium|high|critical)$"),
    metric: str | None = Query(None, max_length=200),
    country_code: str | None = Query(None, max_length=10),
    acknowledged: bool | None = Query(None),
    alert_type: str | None = Query(None, pattern=r"^(anomaly|threshold|trend_break)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
) -> AlertListResponse:
    """List signal alerts with optional filters.

    Alerts are global (not org-scoped) since market data is platform-wide.
    Requires authenticated user.
    """
    filters = []
    if severity:
        filters.append(SignalAlert.severity == severity)
    if metric:
        filters.append(SignalAlert.metric == metric)
    if country_code:
        filters.append(SignalAlert.country_code == country_code)
    if acknowledged is not None:
        filters.append(SignalAlert.acknowledged == acknowledged)
    if alert_type:
        filters.append(SignalAlert.alert_type == alert_type)

    base_query = (
        select(SignalAlert).where(*filters).order_by(SignalAlert.created_at.desc())
    )

    total_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = total_result.scalar_one()

    unack_filters = list(filters) + [SignalAlert.acknowledged == False]
    unack_result = await db.execute(
        select(func.count(SignalAlert.id)).where(*unack_filters)
    )
    unacknowledged = unack_result.scalar_one()

    items_result = await db.execute(base_query.offset(skip).limit(limit))
    items = items_result.scalars().all()

    return AlertListResponse(
        items=[_to_response(a) for a in items],
        total=total,
        unacknowledged=unacknowledged,
    )


@router.get("/summary", response_model=AlertSummaryResponse)
async def get_alert_summary(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
) -> AlertSummaryResponse:
    """Aggregated alert counts broken down by severity and top metrics."""
    total_result = await db.execute(select(func.count(SignalAlert.id)))
    total = total_result.scalar_one()

    unack_result = await db.execute(
        select(func.count(SignalAlert.id)).where(SignalAlert.acknowledged == False)
    )
    unacknowledged = unack_result.scalar_one()

    severity_rows = await db.execute(
        select(SignalAlert.severity, func.count(SignalAlert.id).label("cnt")).group_by(
            SignalAlert.severity
        )
    )
    by_severity = {row.severity: row.cnt for row in severity_rows}

    metric_rows = await db.execute(
        select(SignalAlert.metric, func.count(SignalAlert.id).label("cnt"))
        .where(SignalAlert.metric.isnot(None))
        .group_by(SignalAlert.metric)
        .order_by(func.count(SignalAlert.id).desc())
        .limit(10)
    )
    by_metric = {row.metric: row.cnt for row in metric_rows}

    return AlertSummaryResponse(
        total=total,
        unacknowledged=unacknowledged,
        by_severity=by_severity,
        by_metric=by_metric,
    )


@router.post("/{alert_id}/acknowledge", response_model=AcknowledgeResponse)
async def acknowledge_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
) -> AcknowledgeResponse:
    """Acknowledge a signal alert (mark as reviewed)."""
    from datetime import timezone

    result = await db.execute(select(SignalAlert).where(SignalAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    if not alert.acknowledged or alert.acknowledged_at is None:
        alert.acknowledged = True
        alert.acknowledged_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(alert)

    return AcknowledgeResponse(
        id=str(alert.id),
        acknowledged=alert.acknowledged,
        acknowledged_at=alert.acknowledged_at,
    )


# ── Helper ─────────────────────────────────────────────────────────────────────


def _to_response(alert: SignalAlert) -> AlertResponse:
    return AlertResponse(
        id=str(alert.id),
        alert_type=alert.alert_type,
        severity=alert.severity,
        metric=alert.metric,
        country_code=alert.country_code,
        title=alert.title,
        description=alert.description,
        current_value=alert.current_value,
        baseline_value=alert.baseline_value,
        deviation_pct=alert.deviation_pct,
        acknowledged=alert.acknowledged,
        acknowledged_at=alert.acknowledged_at,
        created_at=alert.created_at,
    )
