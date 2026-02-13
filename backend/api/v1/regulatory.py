"""Regulatory Knowledge API endpoints.

Dynamic, learning-oriented regulatory intelligence management.
Allows domain experts to add, update, and verify regulatory knowledge.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user, require_permissions
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.services.regulatory_intelligence import RegulatoryIntelligenceService

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


# === Endpoints ===


@router.post("/events", status_code=201)
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
    from uuid import uuid4

    from backend.models.regulatory_knowledge import RegulatoryEvent

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
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """List regulatory events in knowledge base.

    Shows the dynamic regulatory intelligence accumulated over time.
    """
    from sqlalchemy import and_, desc, select

    from backend.models.regulatory_knowledge import RegulatoryEvent

    filters = []

    if issuing_body:
        filters.append(RegulatoryEvent.issuing_body == issuing_body)

    if event_type:
        filters.append(RegulatoryEvent.event_type == event_type)

    if sector:
        filters.append(RegulatoryEvent.affected_sectors.contains([sector]))

    if verified_only:
        filters.append(RegulatoryEvent.verified_by_expert == True)

    query = (
        select(RegulatoryEvent)
        .where(and_(*filters) if filters else True)
        .order_by(desc(RegulatoryEvent.announced_at))
        .limit(limit)
    )

    result = await db.execute(query)
    events = result.scalars().all()

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


@router.post("/rules", status_code=201)
async def create_regulatory_rule(
    body: RegulatoryRuleCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["manage_regulatory_knowledge"])),
):
    """Create a new regulatory rule.

    Experts can codify regulatory requirements as structured rules
    that the system can automatically apply to signals.
    """
    from uuid import uuid4

    from backend.models.regulatory_knowledge import RegulatoryRule

    rule = RegulatoryRule(
        id=uuid4(),
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

    db.add(rule)
    await db.commit()

    return {
        "id": str(rule.id),
        "rule_type": rule.rule_type,
        "description": rule.description,
    }


@router.post("/impacts", status_code=201)
async def record_regulatory_impact(
    body: RegulatoryImpactCreate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["manage_regulatory_knowledge"])),
):
    """Record observed impact of a regulatory event.

    This is the learning mechanism — as experts observe actual impacts,
    the system learns to predict future impacts better.
    """
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
    from backend.models.signal import Signal

    # Get signal
    signal = await db.get(Signal, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    # Apply regulatory intelligence
    service = RegulatoryIntelligenceService(db)
    context = await service.enrich_signal_with_regulatory_context(signal)

    return SignalEnrichmentResponse(**context)


@router.post("/signals/{signal_id}/extract-event")
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
    from backend.models.signal import Signal

    signal = await db.get(Signal, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

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


@router.patch("/rules/{rule_id}/feedback")
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
    service = RegulatoryIntelligenceService(db)
    await service.update_rule_accuracy(rule_id, was_accurate)
    await db.commit()

    return {
        "rule_id": str(rule_id),
        "feedback_recorded": True,
        "was_accurate": was_accurate,
    }


@router.get("/stats")
async def get_regulatory_knowledge_stats(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get statistics about regulatory knowledge base.

    Shows how much the system has learned over time.
    """
    from sqlalchemy import func, select

    from backend.models.regulatory_knowledge import (
        RegulatoryEvent,
        RegulatoryImpact,
        RegulatoryRule,
    )

    # Count events by issuing body
    events_by_body = await db.execute(
        select(
            RegulatoryEvent.issuing_body, func.count(RegulatoryEvent.id).label("count")
        ).group_by(RegulatoryEvent.issuing_body)
    )

    # Count verified vs. auto-extracted
    verified_count = await db.execute(
        select(func.count(RegulatoryEvent.id)).where(
            RegulatoryEvent.verified_by_expert == True
        )
    )

    total_events = await db.execute(select(func.count(RegulatoryEvent.id)))

    total_rules = await db.execute(
        select(func.count(RegulatoryRule.id)).where(RegulatoryRule.is_active == True)
    )

    total_impacts = await db.execute(select(func.count(RegulatoryImpact.id)))

    return {
        "total_events": total_events.scalar_one(),
        "verified_events": verified_count.scalar_one(),
        "active_rules": total_rules.scalar_one(),
        "recorded_impacts": total_impacts.scalar_one(),
        "events_by_regulator": [
            {"regulator": row[0], "count": row[1]} for row in events_by_body
        ],
        "knowledge_base_age_days": 0,  # TODO: Calculate from first event
        "learning_velocity": "Growing",  # TODO: Calculate trend
    }


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
    response_model=dict,
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
        raise HTTPException(
            status_code=500, detail=f"Pattern learning failed: {str(e)}"
        )


@router.get(
    "/patterns",
    response_model=list[PatternResponse],
    summary="List learned regulatory patterns",
    description="Retrieve all discovered regulatory patterns with metadata",
)
async def list_regulatory_patterns(
    pattern_type: str | None = Query(None, description="Filter by pattern type"),
    min_confidence: float = Query(0.5, ge=0, le=1),
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
    from sqlalchemy import and_, select

    from backend.models.regulatory_knowledge import RegulatoryPattern

    filters = [RegulatoryPattern.confidence_score >= min_confidence]

    if pattern_type:
        filters.append(RegulatoryPattern.pattern_type == pattern_type)

    query = (
        select(RegulatoryPattern)
        .where(and_(*filters))
        .order_by(RegulatoryPattern.confidence_score.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    patterns = result.scalars().all()

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
    from backend.models.regulatory_knowledge import RegulatoryEvent

    event = await db.get(RegulatoryEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Regulatory event not found")

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
            for p in predictions
        ]

    except Exception as e:
        logger.error(f"Prediction failed for event {event_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
