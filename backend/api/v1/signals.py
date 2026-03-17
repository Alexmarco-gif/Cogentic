"""Signals API endpoints.

Browse, filter, search, and query signal catalog.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db_read
from backend.repositories.signal import SignalRepository
from backend.schemas.signals import (
    IntelligenceSignalResponse,
    SignalDetailResponse,
    SignalListResponse,
    SignalResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/signals")


_SIGNAL_TYPE_PATTERN = r"^(news|social|regulatory|financial|market|technology)$"


@router.get("", response_model=SignalListResponse)
async def list_signals(
    signal_type: str | None = Query(None, description="Filter by type", pattern=_SIGNAL_TYPE_PATTERN),
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    """Browse/filter/search signal catalog."""
    repo = SignalRepository(db)

    if signal_type:
        items = await repo.get_by_type(
            signal_type,
            org_id=auth.org_id,
            min_confidence=min_confidence,
            skip=skip,
            limit=limit,
        )
    else:
        items = await repo.get_visible(org_id=auth.org_id, skip=skip, limit=limit)

    total = await repo.count_visible(org_id=auth.org_id)
    return SignalListResponse(
        items=[SignalResponse.model_validate(s) for s in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/trending", response_model=list[SignalResponse])
async def get_trending_signals(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    """Get ML-ranked trending signals (scored by anomaly + confidence models).

    Different from /feedback/trending which ranks by user engagement.
    This endpoint uses ML scoring pipelines for ranking.
    """
    repo = SignalRepository(db)
    signals = await repo.get_trending(org_id=auth.org_id, skip=skip, limit=limit)
    return [SignalResponse.model_validate(s) for s in signals]


@router.get("/feed", response_model=SignalListResponse)
async def get_signal_feed(
    industry_id: UUID | None = Query(None),
    signal_type: str | None = Query(None, pattern=_SIGNAL_TYPE_PATTERN),
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    """Real-time signal feed (paginated, filterable)."""
    repo = SignalRepository(db)
    items = await repo.get_feed(
        org_id=auth.org_id,
        industry_id=industry_id,
        signal_type=signal_type,
        min_confidence=min_confidence,
        skip=skip,
        limit=limit,
    )
    total = await repo.count_visible(org_id=auth.org_id)
    return SignalListResponse(
        items=[SignalResponse.model_validate(s) for s in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/feed/intelligence", response_model=list[IntelligenceSignalResponse])
async def get_intelligence_feed(
    industry_id: UUID | None = Query(None),
    signal_type: str | None = Query(None, pattern=_SIGNAL_TYPE_PATTERN),
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
    country: str | None = Query(None, description="ISO 3166-1 alpha-3 filter e.g. NGA"),
    latest_only: bool = Query(True, description="Exclude superseded signal versions"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    """Intelligence-enriched signal feed.

    Extends the base feed with ML scores, NER top entities, causal summaries,
    regulatory flags, and geographic focus — all in a single response.
    Filters out superseded (amended) signal versions by default.
    """
    from sqlalchemy.orm import selectinload

    from backend.models.causal_event import CausalEvent
    from backend.models.signal import Signal
    from backend.models.signal_score import SignalScore

    # Build base query
    stmt = (
        select(Signal)
        .options(
            selectinload(Signal.scores),
        )
        .where(Signal.confidence >= min_confidence)
    )

    # Org scoping: global signals (org_id=NULL) + org's own signals
    from sqlalchemy import or_

    stmt = stmt.where(
        or_(Signal.org_id.is_(None), Signal.org_id == auth.org_id)
    )

    if latest_only:
        # Only return signals not yet superseded
        stmt = stmt.where(Signal.superseded_by_id.is_(None))

    if signal_type:
        stmt = stmt.where(Signal.signal_type == signal_type)

    if country:
        # Match on extracted_data->>'country_code' or provenance country_context
        from sqlalchemy import cast, func
        from sqlalchemy.dialects.postgresql import JSONB

        stmt = stmt.where(
            or_(
                Signal.extracted_data["country_code"].astext == country,
                Signal.provenance["country_context"].astext == country,
            )
        )

    stmt = stmt.order_by(Signal.fetched_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    signals = result.scalars().all()

    # Batch load causal events for all signal IDs
    signal_ids = [s.id for s in signals]
    causal_map: dict[UUID, CausalEvent] = {}
    if signal_ids:
        causal_result = await db.execute(
            select(CausalEvent)
            .where(CausalEvent.signal_id.in_(signal_ids))
            .order_by(CausalEvent.created_at.desc())
        )
        for ce in causal_result.scalars().all():
            if ce.signal_id not in causal_map:
                causal_map[ce.signal_id] = ce

    # Build enriched responses
    enriched = []
    for sig in signals:
        base = IntelligenceSignalResponse.model_validate(sig)

        # ML scores
        score_map = {ss.score_type: ss.score_value for ss in (sig.scores or [])}
        base.anomaly_score = score_map.get("anomaly")
        base.trending_score = score_map.get("trending")

        # Top entities from provenance or extracted_data
        ed = sig.extracted_data or {}
        entities_raw = ed.get("entities", [])
        base.top_entities = entities_raw[:5] if isinstance(entities_raw, list) else []

        # Geographic focus
        geo_list = ed.get("geographic", [])
        if isinstance(geo_list, list) and geo_list:
            top_geo = geo_list[0]
            base.primary_country = top_geo.get("country_code")
            base.primary_region = top_geo.get("parent_region")

        # Causal intelligence
        ce = causal_map.get(sig.id)
        if ce:
            base.causal_summary = ce.event_summary
            base.causal_event_type = ce.event_type

        # Regulatory flag from extracted_data
        reg_flags = ed.get("regulatory_flags", [])
        if isinstance(reg_flags, list) and reg_flags:
            flag = reg_flags[0]
            base.regulatory_flag = flag.get("flag_type") if isinstance(flag, dict) else str(flag)
            base.regulatory_body = flag.get("body") if isinstance(flag, dict) else None

        enriched.append(base)

    return enriched


@router.get("/regions")
async def get_signal_regions(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    """Aggregate signals by region for the domain map.

    Returns a list of region summaries with signal counts, severity,
    top signal, and opportunity scores, derived from the signal
    extracted_data JSONB field.
    """

    repo = SignalRepository(db)
    signals = await repo.get_visible(org_id=auth.org_id, skip=0, limit=500)

    # Group signals by region (state field in extracted_data)
    region_map: dict[str, dict] = {}
    for s in signals:
        ed = s.extracted_data or {}
        state = (
            ed.get("region") or ed.get("state") or ed.get("location", {}).get("state")
            if isinstance(ed.get("location"), dict)
            else ed.get("region") or ed.get("state")
        )
        if not state:
            continue

        if state not in region_map:
            region_map[state] = {
                "id": state.lower().replace(" ", "-"),
                "name": state,
                "state": state,
                "lat": ed.get("lat", 9.0 + hash(state) % 5),
                "lng": ed.get("lng", 3.0 + hash(state) % 8),
                "signalCount": 0,
                "severity": "low",
                "domains": set(),
                "topSignal": "",
                "riskLevel": "stable",
                "opportunityScore": 50,
                "summary": "",
                "_max_confidence": 0.0,
            }

        rm = region_map[state]
        rm["signalCount"] += 1
        if s.signal_type:
            rm["domains"].add(s.signal_type)
        if s.confidence and s.confidence > rm["_max_confidence"]:
            rm["_max_confidence"] = s.confidence
            rm["topSignal"] = s.title or ""

    # Compute severity/risk based on signal count
    for rm in region_map.values():
        count = rm["signalCount"]
        if count >= 10:
            rm["severity"] = "critical"
            rm["riskLevel"] = "critical"
        elif count >= 5:
            rm["severity"] = "high"
            rm["riskLevel"] = "elevated"
        elif count >= 2:
            rm["severity"] = "medium"
            rm["riskLevel"] = "moderate"
        rm["domains"] = sorted(rm["domains"])
        rm["opportunityScore"] = min(100, int(rm["_max_confidence"] * 100))
        rm["summary"] = f"{count} signals detected in {rm['name']}"
        del rm["_max_confidence"]

    return list(region_map.values())


@router.get("/{signal_id}", response_model=SignalDetailResponse)
async def get_signal(
    signal_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    """Get single signal detail + entity links."""
    repo = SignalRepository(db)
    signal = await repo.get(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    # Enforce org-scoping: only allow access to global signals or signals
    # belonging to the user's org (prevents cross-tenant data leak)
    if signal.org_id is not None and signal.org_id != auth.org_id:
        raise HTTPException(status_code=404, detail="Signal not found")
    return SignalDetailResponse.model_validate(signal)


@router.get("/entity/{entity_id}", response_model=SignalListResponse)
async def get_signals_by_entity(
    entity_id: UUID,
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    """Get all signals linked to a given entity."""
    repo = SignalRepository(db)
    items = await repo.get_by_entity(
        entity_id,
        org_id=auth.org_id,
        min_confidence=min_confidence,
        skip=skip,
        limit=limit,
    )
    return SignalListResponse(
        items=[SignalResponse.model_validate(s) for s in items],
        total=len(items),
        skip=skip,
        limit=limit,
    )


@router.get("/contract/{contract_id}", response_model=SignalListResponse)
async def get_signals_by_contract(
    contract_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_read),
):
    """Get all signals from a specific contract."""
    repo = SignalRepository(db)
    items = await repo.get_by_contract(
        contract_id, org_id=auth.org_id, skip=skip, limit=limit
    )
    total = await repo.count_by_contract(contract_id)
    return SignalListResponse(
        items=[SignalResponse.model_validate(s) for s in items],
        total=total,
        skip=skip,
        limit=limit,
    )
