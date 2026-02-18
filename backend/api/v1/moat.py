"""Moat Metrics Dashboard API endpoints.

Provides the full intelligence moat health dashboard, individual metric
computation, snapshot management, prediction backtesting, and
replicability blind testing.

Implements all 5 success metrics from the strategy doc:
  1. Entity Graph Coverage — 1,000+ Nigerian entities
  2. Causal Chains Discovered — 50+ validated chains
  3. Prediction Accuracy — >70% on 7-day forecasts
  4. Replicability Score — <20% ChatGPT-replicable
  5. User Retention (DAU/MAU) — >0.4
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user, require_permissions
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.services.moat_metrics import MoatMetricsService
from backend.services.prediction_backtest import PredictionBacktestService
from backend.services.replicability_test import ReplicabilityBlindTestService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/moat")


# ── Schemas ──────────────────────────────────────────────────────────


class MetricSummary(BaseModel):
    metric: str
    target: Any
    current: Any
    progress_pct: float
    meets_target: bool
    details: dict


class DashboardResponse(BaseModel):
    computed_at: str
    moat_health_score: float
    targets_met: str
    overall_status: str
    metrics: dict[str, MetricSummary]
    targets: dict


class SnapshotResponse(BaseModel):
    id: str
    snapshot_date: str
    entity_count: int
    entity_verified_count: int
    entity_relationship_count: int
    entity_source_profile_count: int
    causal_event_count: int
    causal_edge_count: int
    causal_chain_count: int
    prediction_total: int
    prediction_accurate: int
    prediction_inaccurate: int
    prediction_accuracy_pct: float | None
    replicability_tests_run: int
    replicability_score_pct: float | None
    dau: int
    mau: int
    dau_mau_ratio: float | None
    moat_health_score: float | None
    details: dict
    created_at: str


class BacktestResponse(BaseModel):
    accuracy_pct: float | None
    total_predictions_tested: int
    accurate: int | None = None
    inaccurate: int | None = None
    lookback_days: int
    forecast_horizon_days: int
    meets_target: bool | None = None
    pair_breakdown: list[dict] | None = None
    note: str | None = None


class BacktestChainRequest(BaseModel):
    cause_event_type: str = Field(..., min_length=1)
    effect_event_type: str = Field(..., min_length=1)
    lookback_days: int = Field(180, ge=30, le=730)
    forecast_horizon_days: int = Field(14, ge=1, le=90)


class ReplicabilityResponse(BaseModel):
    replicability_score_pct: float
    tests_run: int
    meets_target: bool
    baseline_model: str
    dimensions: dict | None = None
    test_results: list[dict] | None = None
    note: str | None = None
    data_depth: dict | None = None


class SnapshotCreateResponse(BaseModel):
    """Response for taking a new snapshot."""

    id: str
    snapshot_date: Any
    moat_health_score: float | None


class SnapshotTrendResponse(BaseModel):
    """Response for snapshot trend data."""

    days_requested: int
    data_points: int
    trend: list[dict[str, Any]]


# ── Dashboard Endpoints ──────────────────────────────────────────────


@router.get("/dashboard", response_model=dict[str, Any])
async def get_moat_dashboard(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get the full moat health dashboard with all 5 metrics.

    Computes every metric in real-time and returns the composite
    health score plus per-metric breakdowns.
    """
    service = MoatMetricsService(db)
    return await service.compute_all_metrics()


@router.get("/metrics/entity-graph", response_model=dict[str, Any])
async def get_entity_graph_coverage(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Metric 1: Entity Graph Coverage.

    Target: 1,000+ Nigerian entities with cross-source profiles.
    """
    service = MoatMetricsService(db)
    return await service.compute_entity_graph_coverage()


@router.get("/metrics/causal-chains", response_model=dict[str, Any])
async def get_causal_chains_discovered(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Metric 2: Causal Chains Discovered.

    Target: 50+ validated causal chains with confidence >= 0.6.
    """
    service = MoatMetricsService(db)
    return await service.compute_causal_chains_discovered()


@router.get("/metrics/prediction-accuracy", response_model=dict[str, Any])
async def get_prediction_accuracy(
    lookback_days: int = Query(default=90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Metric 3: Prediction Accuracy (Moat KPI).

    Computes accuracy from causal edge backtesting + user validation.
    Different from /feedback/predictions/accuracy which uses only
    user-submitted feedback validation data.

    Target: >70% on 7-day forecasts.
    """
    service = MoatMetricsService(db)
    return await service.compute_prediction_accuracy(lookback_days)


@router.get("/metrics/replicability", response_model=dict[str, Any])
async def get_replicability_score(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Metric 4: Replicability Score.

    Target: <20% ChatGPT-replicable. Uses intelligence layer analysis
    or data coverage heuristic when synthesis context is unavailable.
    """
    service = MoatMetricsService(db)
    return await service.compute_replicability_score()


@router.get("/metrics/user-retention", response_model=dict[str, Any])
async def get_user_retention(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Metric 5: User Retention (DAU/MAU).

    Target: >0.4 ratio (strong stickiness).
    """
    service = MoatMetricsService(db)
    return await service.compute_user_retention()


# ── Snapshot Endpoints ───────────────────────────────────────────────


@router.post("/snapshots", status_code=201, response_model=SnapshotCreateResponse)
async def take_snapshot(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Take a point-in-time snapshot of all moat metrics.

    Snapshots are stored in the database and used for trend analysis.
    Designed to be called daily (via cron/scheduler) or on-demand.
    Requires admin or owner role.
    """
    service = MoatMetricsService(db)
    snapshot = await service.take_snapshot()
    await db.commit()

    return {
        "id": str(snapshot.id),
        "snapshot_date": snapshot.snapshot_date,
        "moat_health_score": snapshot.moat_health_score,
    }


@router.get("/snapshots/latest", response_model=dict[str, Any])
async def get_latest_snapshot(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get the most recent daily snapshot."""
    service = MoatMetricsService(db)
    snapshot = await service.get_latest_snapshot()
    if not snapshot:
        return {"message": "No snapshots yet. Take one first via POST /moat/snapshots."}
    return snapshot


@router.get("/snapshots/trend", response_model=SnapshotTrendResponse)
async def get_snapshot_trend(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get daily snapshot trend for the past N days.

    Enables moat health charting over time.
    """
    service = MoatMetricsService(db)
    trend = await service.get_snapshot_trend(days)
    return {"days_requested": days, "data_points": len(trend), "trend": trend}


# ── Backtest Endpoints ───────────────────────────────────────────────


@router.get("/backtest", response_model=dict[str, Any])
async def run_backtest(
    lookback_days: int = Query(default=90, ge=7, le=365),
    forecast_horizon_days: int = Query(default=7, ge=1, le=90),
    min_edge_confidence: float = Query(default=0.5, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Run systematic prediction backtest.

    Tests all causal edges created within the lookback window whose
    forecast windows have fully elapsed, checking if predicted effects
    actually occurred.
    """
    service = PredictionBacktestService(db)
    return await service.run_backtest(
        lookback_days=lookback_days,
        forecast_horizon_days=forecast_horizon_days,
        min_edge_confidence=min_edge_confidence,
    )


@router.post("/backtest/chain", response_model=dict[str, Any])
async def backtest_specific_chain(
    body: BacktestChainRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Backtest a specific cause → effect causal chain.

    Finds all historical instances of the cause event and checks
    whether the effect occurred within the forecast horizon.
    """
    service = PredictionBacktestService(db)
    return await service.backtest_specific_chain(
        cause_event_type=body.cause_event_type,
        effect_event_type=body.effect_event_type,
        lookback_days=body.lookback_days,
        forecast_horizon_days=body.forecast_horizon_days,
    )


@router.get("/backtest/all-chains", response_model=dict[str, Any])
async def backtest_all_chains(
    lookback_days: int = Query(default=180, ge=30, le=730),
    forecast_horizon_days: int = Query(default=7, ge=1, le=90),
    min_edge_confidence: float = Query(default=0.6, ge=0, le=1),
    min_observations: int = Query(default=2, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Backtest all known causal chains with sufficient data.

    Iterates over all distinct cause→effect type pairs in the causal
    edge table that meet confidence and observation thresholds.
    """
    service = PredictionBacktestService(db)
    return await service.backtest_all_known_chains(
        lookback_days=lookback_days,
        forecast_horizon_days=forecast_horizon_days,
        min_edge_confidence=min_edge_confidence,
        min_observations=min_observations,
    )


# ── Replicability Blind Test Endpoints ───────────────────────────────


@router.post("/replicability/blind-test", response_model=dict[str, Any])
async def run_blind_test(
    sample_size: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Run a blind replicability test against baseline LLM.

    Compares ESIP synthesis outputs with vanilla GPT-4o responses
    to the same queries. Measures semantic overlap, entity overlap,
    specificity gap, and causal insight uniqueness.

    Uses OpenAI credits — use judiciously.
    Requires admin or owner role.
    """
    service = ReplicabilityBlindTestService(db)
    return await service.run_blind_test(sample_size=sample_size)
