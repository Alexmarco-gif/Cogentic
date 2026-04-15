"""Regulatory Knowledge API endpoints.

Dynamic, learning-oriented regulatory intelligence management.
Allows domain experts to add, update, and verify regulatory knowledge.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user, require_permissions
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.models.regulatory_knowledge import RegulatoryEvent
from backend.models.signal import Signal
from backend.repositories.regulatory import RegulatoryRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/regulatory", tags=["regulatory-knowledge"])


# === Schemas ===


class RegulatoryEventCreate(BaseModel):
    """Create new regulatory event (expert input)."""

    event_type: str = Field(..., description="Type of regulatory event")
    title: str = Field(..., min_length=10, max_length=500)
    description: str = Field(..., min_length=50)
    issuing_body: str = Field(..., description="Regulatory body (CBN, SEC, etc.)")
    announced_at: datetime
    effective_date: datetime | None = None
    deadline_date: datetime | None = None
    affected_sectors: list[str] = Field(default_factory=list)
    affected_entity_types: list[str] = Field(default_factory=list)
    severity_score: float = Field(0.5, ge=0, le=1)
    compliance_complexity: float = Field(0.5, ge=0, le=1)
    requirements: dict = Field(default_factory=dict)
    expert_notes: str | None = None


class RegulatoryEventResponse(BaseModel):
    """Regulatory event response."""

    id: str
    event_type: str
    title: str
    issuing_body: str
    announced_at: str
    severity_score: float
    verified_by_expert: bool
    confidence_score: float
    affected_sectors: list[str]


class RegulatoryRuleCreate(BaseModel):
    """Create new regulatory rule."""

    rule_type: str
    rule_category: str
    condition: dict = Field(..., description="JSON logic for when rule applies")
    action: dict = Field(..., description="What happens when rule applies")
    description: str = Field(..., min_length=20)
    interpretation_guidance: str | None = None
    source_event_id: UUID | None = None
    effective_from: datetime
    effective_until: datetime | None = None
    applicable_sectors: list[str] = Field(default_factory=list)
    applicable_entity_types: list[str] = Field(default_factory=list)


class RegulatoryImpactCreate(BaseModel):
    """Record observed impact of regulatory event."""

    regulatory_event_id: UUID
    impact_type: str = Field(..., description="Type of impact observed")
    metric_name: str = Field(..., description="Metric affected")
    baseline_value: float
    post_impact_value: float
    affected_entity_id: UUID | None = None
    affected_sector: str | None = None
    supporting_signal_ids: list[UUID] = Field(default_factory=list)
    description: str
    confounding_factors: str | None = None


class SignalEnrichmentResponse(BaseModel):
    """Signal enriched with regulatory context."""

    has_regulatory_implications: bool
    issuing_body: str | None = None
    event_type: str | None = None
    severity_score: float | None = None
    regulatory_events: list[dict]
    applicable_rules: list[dict]
    predicted_impacts: list[dict]
    historical_precedents: list[dict]
    interpretation: str | None = None


class EventCreateResponse(BaseModel):
    """Response for creating a regulatory event."""

    id: str
    event_type: str
    title: str
    verified: bool


class RuleCreateResponse(BaseModel):
    """Response for creating a regulatory rule."""

    id: str
    rule_type: str
    description: str


class ImpactCreateResponse(BaseModel):
    """Response for recording a regulatory impact."""

    id: str
    impact_type: str
    percentage_change: float | None = None
    lag_days: int | None = None


class EventExtractionResponse(BaseModel):
    """Response for signal event extraction."""

    extracted: bool | None = None
    detected: bool | None = None
    event_id: str | None = None
    event_type: str | None = None
    issuing_body: str | None = None
    severity_score: float | None = None
    message: str | None = None


class RuleFeedbackResponse(BaseModel):
    """Response for rule feedback."""

    rule_id: str
    feedback_recorded: bool
    was_accurate: bool


class RegulatoryStatsResponse(BaseModel):
    """Response for regulatory knowledge stats."""

    knowledge_base_age_days: int
    learning_velocity: str
    model_config = {"extra": "allow"}


class PatternLearningResponse(BaseModel):
    """Response for pattern learning."""

    total_patterns_discovered: int
    patterns_by_type: dict[str, list[dict[str, Any]]]
    lookback_months: int
    min_occurrences: int


# === Endpoints ===


@router.post("/events", status_code=201, response_model=EventCreateResponse)
async def create_regulatory_event(
    body: RegulatoryEventCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["manage_regulatory_knowledge"])),
):
    """Create a new regulatory event (expert input).

    This is how domain experts add regulatory intelligence that
    the system couldn't automatically extract.

    Requires: Domain expert or admin permissions
    """
    event = RegulatoryEvent(
        id=uuid4(),
        event_type=body.event_type,
        title=body.title,
        description=body.description,
        issuing_body=body.issuing_body,
        announced_at=body.announced_at,
        effective_date=body.effective_date,
        deadline_date=body.deadline_date,
        affected_sectors=body.affected_sectors,
        affected_entity_types=body.affected_entity_types,
        severity_score=body.severity_score,
        compliance_complexity=body.compliance_complexity,
        requirements=body.requirements,
        verified_by_expert=True,  # Expert-created = verified
        expert_notes=body.expert_notes,
        confidence_score=0.95,  # High confidence for expert input
    )

    db.add(event)
    await db.commit()

    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "title": event.title,
        "verified": True,
    }


@router.get("/events", response_model=list[RegulatoryEventResponse])
async def list_regulatory_events(
    issuing_body: str | None = Query(None, description="Filter by regulatory body"),
    event_type: str | None = Query(None, description="Filter by event type"),
    sector: str | None = Query(None, description="Filter by affected sector"),
    verified_only: bool = Query(True, description="Only show expert-verified events"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """List regulatory events in knowledge base.

    Shows the dynamic regulatory intelligence accumulated over time.
    """
    repo = RegulatoryRepository(db)
    events = await repo.list_events(
        issuing_body=issuing_body,
        event_type=event_type,
        sector=sector,
        verified_only=verified_only,
        skip=skip,
        limit=limit,
    )

    return [
        RegulatoryEventResponse(
            id=str(e.id),
            event_type=e.event_type,
            title=e.title,
            issuing_body=e.issuing_body,
            announced_at=e.announced_at.isoformat(),
            severity_score=e.severity_score,
            verified_by_expert=e.verified_by_expert,
            confidence_score=e.confidence_score,
            affected_sectors=e.affected_sectors,
        )
        for e in events
    ]


@router.post("/rules", status_code=201, response_model=RuleCreateResponse)
async def create_regulatory_rule(
    body: RegulatoryRuleCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["manage_regulatory_knowledge"])),
):
    """Create a new regulatory rule.

    Experts can codify regulatory requirements as structured rules
    that the system can automatically apply to signals.
    """
    repo = RegulatoryRepository(db)
    rule = await repo.create_rule(
        rule_type=body.rule_type,
        rule_category=body.rule_category,
        condition=body.condition,
        action=body.action,
        description=body.description,
        interpretation_guidance=body.interpretation_guidance,
        source_event_id=body.source_event_id,
        effective_from=body.effective_from,
        effective_until=body.effective_until,
        applicable_sectors=body.applicable_sectors,
        applicable_entity_types=body.applicable_entity_types,
        is_active=True,
        verified_by_expert=True,
        confidence_score=0.9,
    )
    await db.commit()

    return {
        "id": str(rule.id),
        "rule_type": rule.rule_type,
        "description": rule.description,
    }


@router.post("/impacts", status_code=201, response_model=ImpactCreateResponse)
async def record_regulatory_impact(
    body: RegulatoryImpactCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["manage_regulatory_knowledge"])),
):
    """Record observed impact of a regulatory event.

    This is the learning mechanism — as experts observe actual impacts,
    the system learns to predict future impacts better.
    """
    from backend.services.regulatory_intelligence import RegulatoryIntelligenceService

    service = RegulatoryIntelligenceService(db)

    impact = await service.record_regulatory_impact(
        regulatory_event_id=body.regulatory_event_id,
        impact_type=body.impact_type,
        metric_name=body.metric_name,
        baseline_value=body.baseline_value,
        post_impact_value=body.post_impact_value,
        affected_entity_id=body.affected_entity_id,
        affected_sector=body.affected_sector,
        supporting_signal_ids=body.supporting_signal_ids,
        description=body.description,
        expert_verified=True,
    )

    await db.commit()

    return {
        "id": str(impact.id),
        "impact_type": impact.impact_type,
        "percentage_change": impact.percentage_change,
        "lag_days": impact.lag_days,
    }


@router.post("/signals/{signal_id}/enrich", response_model=SignalEnrichmentResponse)
async def enrich_signal_with_regulatory_context(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Apply regulatory intelligence to a signal.

    This demonstrates the contextual interpretation layer —
    generic AI can't provide this depth of regulatory analysis.
    """
    # Get signal
    signal = await db.get(Signal, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    # Apply regulatory intelligence
    from backend.services.regulatory_intelligence import RegulatoryIntelligenceService

    service = RegulatoryIntelligenceService(db)
    context = await service.enrich_signal_with_regulatory_context(signal)

    return SignalEnrichmentResponse(**context)


@router.post(
    "/signals/{signal_id}/extract-event", response_model=EventExtractionResponse
)
async def extract_regulatory_event_from_signal(
    signal_id: UUID,
    auto_create: bool = Query(
        True, description="Automatically create event if detected"
    ),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["manage_signals"])),
):
    """Automatically extract regulatory event from signal.

    Uses NLP + ML to detect and structure regulatory content.
    """
    signal = await db.get(Signal, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    from backend.services.regulatory_intelligence import RegulatoryIntelligenceService

    service = RegulatoryIntelligenceService(db)
    event = await service.extract_regulatory_event_from_signal(
        signal, auto_create=auto_create
    )

    if auto_create and event:
        await db.commit()
        return {
            "extracted": True,
            "event_id": str(event.id),
            "event_type": event.event_type,
            "issuing_body": event.issuing_body,
            "severity_score": event.severity_score,
        }
    elif event:
        return {
            "detected": True,
            "event_type": event.get("event_type"),
            "issuing_body": event.get("issuing_body"),
            "severity_score": event.get("severity_score"),
        }
    else:
        return {
            "detected": False,
            "message": "No regulatory content detected in signal",
        }


@router.patch("/rules/{rule_id}/feedback", response_model=RuleFeedbackResponse)
async def provide_rule_feedback(
    rule_id: UUID,
    was_accurate: bool = Query(..., description="Was rule application accurate?"),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["manage_regulatory_knowledge"])),
):
    """Provide feedback on rule accuracy (learning loop).

    Experts mark whether a rule was correctly applied,
    and the system adjusts confidence scores accordingly.
    """
    from backend.services.regulatory_intelligence import RegulatoryIntelligenceService

    service = RegulatoryIntelligenceService(db)
    await service.update_rule_accuracy(rule_id, was_accurate)
    await db.commit()

    return {
        "rule_id": str(rule_id),
        "feedback_recorded": True,
        "was_accurate": was_accurate,
    }


@router.get("/stats", response_model=RegulatoryStatsResponse)
async def get_regulatory_knowledge_stats(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get statistics about regulatory knowledge base.

    Shows how much the system has learned over time.
    """
    repo = RegulatoryRepository(db)
    stats = await repo.get_stats()

    return stats


# === Pattern Learning Endpoints ===


class PatternLearningRequest(BaseModel):
    """Request to trigger pattern learning."""

    lookback_months: int = Field(
        36, ge=1, le=120, description="Months of history to analyze"
    )
    min_occurrences: int = Field(
        3, ge=2, le=10, description="Minimum pattern occurrences"
    )


class PatternResponse(BaseModel):
    """Regulatory pattern response."""

    id: str
    pattern_type: str
    pattern_signature: str
    description: str
    occurrence_count: int
    confidence_score: float
    first_observed_at: str
    last_observed_at: str
    metadata: dict


class PredictionResponse(BaseModel):
    """Regulatory action prediction."""

    prediction_type: str
    predicted_event_type: str
    predicted_regulator: str
    confidence: float
    expected_timeframe_days: int | None = None
    expected_date: str | None = None
    days_until_expected: int | None = None
    pattern_id: str
    rationale: str


@router.post(
    "/patterns/learn",
    response_model=PatternLearningResponse,
    summary="Trigger ML pattern learning",
    description="Analyzes historical regulatory events to discover recurring patterns",
)
async def learn_regulatory_patterns(
    request: PatternLearningRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["admin", "analyst"])),
):
    """Discover recurring regulatory patterns using ML sequence mining.

    This endpoint triggers the ML pattern learning process that:
    - Detects event sequences (e.g., consultation → policy → enforcement)
    - Identifies temporal cycles (e.g., rate adjustments every 6 weeks)
    - Discovers cross-regulator cascades
    - Updates pattern confidence scores

    Requires admin or analyst permissions.
    """
    from backend.services.regulatory_intelligence import RegulatoryIntelligenceService

    service = RegulatoryIntelligenceService(db)

    try:
        patterns = await service.learn_patterns_from_history(
            lookback_months=request.lookback_months,
            min_occurrences=request.min_occurrences,
        )

        await db.commit()

        # Group by type
        by_type = {}
        for pattern in patterns:
            ptype = pattern.pattern_type
            if ptype not in by_type:
                by_type[ptype] = []
            by_type[ptype].append(
                {
                    "id": str(pattern.id),
                    "signature": pattern.pattern_signature,
                    "description": pattern.description,
                    "confidence": pattern.confidence_score,
                    "occurrences": pattern.occurrence_count,
                }
            )

        return {
            "total_patterns_discovered": len(patterns),
            "patterns_by_type": by_type,
            "lookback_months": request.lookback_months,
            "min_occurrences": request.min_occurrences,
        }

    except Exception as e:
        logger.error(f"Pattern learning failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Pattern learning failed")


@router.get(
    "/patterns",
    response_model=list[PatternResponse],
    summary="List learned regulatory patterns",
    description="Retrieve all discovered regulatory patterns with metadata",
)
async def list_regulatory_patterns(
    pattern_type: str | None = Query(None, description="Filter by pattern type"),
    min_confidence: float = Query(0.5, ge=0, le=1),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """List all learned regulatory patterns.

    Patterns are discovered through ML analysis of historical events and can:
    - Help predict future regulatory actions
    - Identify typical regulatory sequences
    - Reveal temporal patterns and cycles
    """
    repo = RegulatoryRepository(db)
    patterns = await repo.list_patterns(
        pattern_type=pattern_type,
        min_confidence=min_confidence,
        skip=skip,
        limit=limit,
    )

    return [
        PatternResponse(
            id=str(p.id),
            pattern_type=p.pattern_type,
            pattern_signature=p.pattern_signature,
            description=p.description,
            occurrence_count=p.occurrence_count,
            confidence_score=p.confidence_score,
            first_observed_at=p.first_observed_at.isoformat(),
            last_observed_at=p.last_observed_at.isoformat(),
            metadata=p.metadata_ or {},
        )
        for p in patterns
    ]


@router.get(
    "/events/{event_id}/predictions",
    response_model=list[PredictionResponse],
    summary="Predict follow-on regulatory actions",
    description="Use ML patterns to predict what regulatory actions might follow this event",
)
async def predict_regulatory_actions(
    event_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Predict future regulatory actions based on learned patterns.

    This is the "intelligence moat" — using learned patterns to predict:
    - What regulatory action typically follows this type of event
    - When the next action is likely to occur
    - Which regulators might respond to this event

    Only works if patterns have been learned (via /patterns/learn endpoint).
    """
    event = await db.get(RegulatoryEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Regulatory event not found")

    from backend.services.regulatory_intelligence import RegulatoryIntelligenceService

    service = RegulatoryIntelligenceService(db)

    try:
        predictions = await service.predict_next_regulatory_action(event)

        return [
            PredictionResponse(
                prediction_type=p["prediction_type"],
                predicted_event_type=p["predicted_event_type"],
                predicted_regulator=p["predicted_regulator"],
                confidence=p["confidence"],
                expected_timeframe_days=p.get("expected_timeframe_days"),
                expected_date=p.get("expected_date"),
                days_until_expected=p.get("days_until_expected"),
                pattern_id=p["pattern_id"],
                rationale=p["rationale"],
            )
            for p in predictions[:limit]
        ]

    except Exception as e:
        logger.error(f"Prediction failed for event {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Prediction failed")
