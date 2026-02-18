"""Causal Intelligence API endpoints.

Provides causal chain analysis, impact prediction, historical precedents,
and Granger causality testing — proprietary temporal intelligence.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.ml.causal_inference import CausalInferenceService
from backend.services.causal_intelligence import CausalIntelligenceService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/causal")


# ── Schemas ──────────────────────────────────────────────────────────


class CausalChainResponse(BaseModel):
    chain: list[str]
    lags_days: list[float]
    avg_confidence: float
    total_lag_days: float
    depth: int


class ImpactPredictionResponse(BaseModel):
    trigger_event: str
    time_horizon_days: int
    immediate_impacts: list[dict]
    secondary_impacts: list[dict]
    tertiary_impacts: list[dict]
    total_chains_analyzed: int
    data_coverage: str


class GrangerTestRequest(BaseModel):
    cause_event_type: str = Field(..., min_length=1)
    effect_event_type: str = Field(..., min_length=1)
    max_lag: int = Field(14, ge=1, le=60)
    lookback_days: int = Field(180, ge=30, le=730)


class GrangerTestResponse(BaseModel):
    cause: str
    effect: str
    is_causal: bool
    optimal_lag_days: int | None = None
    p_value: float | None = None
    confidence: float | None = None
    data_points: int | None = None
    interpretation: str | None = None


class SignalImpactResponse(BaseModel):
    signal: dict
    trigger_event: dict
    predictions: dict
    historical_precedents: dict
    affected_entities: list[str]
    analysis_metadata: dict


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/chains/{event_type}", response_model=list[CausalChainResponse])
async def get_causal_chains(
    event_type: str,
    max_depth: int = Query(default=4, ge=1, le=6),
    min_confidence: float = Query(default=0.5, ge=0, le=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get causal chains starting from a specific event type.

    Returns multi-step causal chains discovered from longitudinal data.
    Example: "policy_change" → "lending_rate_increase" → "loan_decline"
    """
    service = CausalIntelligenceService(db)
    chains = await service.find_causal_chains(
        event_type,
        max_depth=max_depth,
        min_confidence=min_confidence,
        limit=limit,
    )
    return [CausalChainResponse(**c) for c in chains]


@router.get("/predict/{event_type}", response_model=ImpactPredictionResponse)
async def predict_impacts(
    event_type: str,
    time_horizon_days: int = Query(default=30, ge=1, le=180),
    min_confidence: float = Query(default=0.5, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Predict cascading impacts from a given event type.

    Uses historical causal chains to forecast immediate, secondary,
    and tertiary impacts with estimated timelines.

    This is proprietary intelligence — no generic AI can replicate
    predictions trained on ESIP's longitudinal event data.
    """
    service = CausalIntelligenceService(db)
    predictions = await service.predict_cascading_impacts(
        event_type,
        time_horizon_days=time_horizon_days,
        min_confidence=min_confidence,
    )
    return ImpactPredictionResponse(**predictions)


@router.post("/granger-test", response_model=GrangerTestResponse)
async def test_granger_causality(
    body: GrangerTestRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Test statistical (Granger) causality between two event types.

    Returns whether past occurrences of the cause event statistically
    predict future occurrences of the effect event.
    """
    service = CausalIntelligenceService(db)
    result = await service.granger_causality_test(
        cause_event_type=body.cause_event_type,
        effect_event_type=body.effect_event_type,
        max_lag=body.max_lag,
        lookback_days=body.lookback_days,
    )

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    return GrangerTestResponse(**result)


@router.get("/signal/{signal_id}/impact", response_model=SignalImpactResponse)
async def analyze_signal_impact(
    signal_id: UUID,
    time_horizon_days: int = Query(default=30, ge=1, le=180),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Analyze cascading impact of a specific signal.

    Flagship proprietary intelligence endpoint. Returns:
      - Triggered causal events
      - Cascading impact predictions with timelines
      - Historical precedents and outcomes
      - Affected entities
    """
    service = CausalIntelligenceService(db)
    result = await service.analyze_signal_impact(
        signal_id, org_id=auth.org_id, time_horizon_days=time_horizon_days
    )
    await db.commit()

    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])

    return SignalImpactResponse(**result)


@router.get("/precedents/{event_type}")
async def get_historical_precedents(
    event_type: str,
    lookback_months: int = Query(default=24, ge=1, le=60),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get historical precedents for an event type.

    Returns past instances and their consequences — the
    "Based on N historical instances..." intelligence.
    """
    service = CausalIntelligenceService(db)
    precedents = await service.find_historical_precedents(
        event_type, lookback_months=lookback_months, limit=limit
    )
    return {"event_type": event_type, "precedents": precedents}


# ── P1 Feature: Counterfactual Analysis ──────────────────────────────


class CounterfactualRequest(BaseModel):
    event_signal_id: str = Field(..., description="Signal ID of the event")
    outcome_metric: str = Field(..., description="Metric to measure (signal type)")
    pre_event_days: int = Field(30, ge=7, le=90)
    post_event_days: int = Field(30, ge=7, le=90)


class CounterfactualResponse(BaseModel):
    event_signal_id: str
    event_date: str
    outcome_metric: str
    causal_impact: dict
    counterfactual: dict
    interpretation: str
    pre_event_fit: dict


@router.post("/counterfactual", response_model=CounterfactualResponse)
async def estimate_counterfactual_impact(
    body: CounterfactualRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Estimate counterfactual: What would have happened if event didn't occur?

    Uses synthetic control method to build baseline prediction and
    measure actual deviation. This is advanced causal inference that
    isolates the true impact of an event from confounding factors.

    Returns:
      - Actual vs. counterfactual baseline comparison
      - Statistical significance of impact
      - Percentage change attributable to event
      - Point-by-point effect timeline
    """
    service = CausalInferenceService(db)
    result = await service.estimate_counterfactual(
        event_signal_id=body.event_signal_id,
        outcome_metric=body.outcome_metric,
        pre_event_days=body.pre_event_days,
        post_event_days=body.post_event_days,
    )

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    return CounterfactualResponse(**result)


class DifferenceInDifferencesRequest(BaseModel):
    treatment_group_metric: str = Field(..., description="Metric for treated group")
    control_group_metric: str = Field(..., description="Metric for control group")
    event_date: str = Field(..., description="Treatment date (ISO format)")
    pre_period_days: int = Field(30, ge=7, le=90)
    post_period_days: int = Field(30, ge=7, le=90)


class DifferenceInDifferencesResponse(BaseModel):
    method: str
    event_date: str
    did_estimate: float
    percentage_effect: float
    decomposition: dict
    cell_values: dict
    interpretation: str


@router.post("/did", response_model=DifferenceInDifferencesResponse)
async def difference_in_differences_analysis(
    body: DifferenceInDifferencesRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Difference-in-differences (DiD) estimation for causal impact.

    Compares change in treatment group vs. control group before/after event.
    Gold standard for causal inference when randomization isn't possible.

    Returns:
      - DiD estimate (treatment effect)
      - Decomposition of treatment vs. control changes
      - Percentage effect
      - All four cell values (treatment/control × pre/post)
    """
    from datetime import datetime

    # Parse event date
    try:
        event_date = datetime.fromisoformat(body.event_date.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid event_date format. Use ISO 8601."
        )

    service = CausalInferenceService(db)
    result = await service.difference_in_differences(
        treatment_group_metric=body.treatment_group_metric,
        control_group_metric=body.control_group_metric,
        event_date=event_date,
        pre_period_days=body.pre_period_days,
        post_period_days=body.post_period_days,
    )

    return DifferenceInDifferencesResponse(**result)
