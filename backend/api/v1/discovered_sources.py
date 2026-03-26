"""Discovered Sources API — manage dynamically discovered signal sources.

Provides endpoints for reviewing, activating, and dismissing data sources
that the system discovers during signal refinement. This powers the
"living contracts" feature where the platform's acquisition aperture
grows dynamically.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user, require_permissions
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.models.discovered_source import DiscoveredSource
from backend.models.signal import Signal
from backend.services.source_discovery import SourceDiscoveryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/discovered-sources", tags=["discovered-sources"])


def _visible_sources_query(auth: AuthContext):
    """Scope discovered-source access to global signals plus the caller org."""
    return (
        select(DiscoveredSource)
        .outerjoin(Signal, Signal.id == DiscoveredSource.first_seen_signal_id)
        .where(or_(Signal.org_id.is_(None), Signal.org_id == auth.org_id))
    )


# ── Schemas ──────────────────────────────────────────────────────────


class DiscoveredSourceResponse(BaseModel):
    id: str
    url: str
    domain: str
    name: str | None
    source_type: str
    signal_type: str | None
    mention_count: int
    relevance_score: float
    status: str
    activated_contract_id: str | None
    created_at: str
    last_seen_at: str


class DiscoveredSourceStatsResponse(BaseModel):
    discovered: int
    recommended: int
    activated: int
    dismissed: int
    total: int


class ActivateSourceRequest(BaseModel):
    industry_id: str = Field(
        ..., description="Industry UUID to associate the contract with"
    )
    name: str | None = Field(None, description="Optional custom contract name")
    description: str | None = None


class ActivateSourceResponse(BaseModel):
    source_id: str
    contract_id: str
    contract_name: str
    source_url: str
    source_type: str
    schedule_tier: str
    message: str


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("", response_model=list[DiscoveredSourceResponse])
async def list_discovered_sources(
    status: str | None = Query(
        None,
        description="Filter by status: discovered, recommended, activated, dismissed",
    ),
    domain: str | None = Query(None, description="Filter by domain substring"),
    min_relevance: float = Query(
        0.0, ge=0, le=1, description="Minimum relevance score"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """List discovered sources with optional filtering.

    Use status=recommended to see the review queue of sources
    the system recommends activating as signal contracts.
    """
    query = _visible_sources_query(auth).order_by(
        DiscoveredSource.relevance_score.desc(),
        DiscoveredSource.mention_count.desc(),
    )

    if status:
        query = query.where(DiscoveredSource.status == status)
    if domain:
        query = query.where(DiscoveredSource.domain.ilike(f"%{domain}%"))
    if min_relevance > 0:
        query = query.where(DiscoveredSource.relevance_score >= min_relevance)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    sources = result.scalars().all()

    return [
        DiscoveredSourceResponse(
            id=str(s.id),
            url=s.url,
            domain=s.domain,
            name=s.name,
            source_type=s.source_type,
            signal_type=s.signal_type,
            mention_count=s.mention_count,
            relevance_score=round(s.relevance_score, 3),
            status=s.status,
            activated_contract_id=str(s.activated_contract_id)
            if s.activated_contract_id
            else None,
            created_at=s.created_at.isoformat() if s.created_at else "",
            last_seen_at=s.last_seen_at.isoformat() if s.last_seen_at else "",
        )
        for s in sources
    ]


@router.get("/recommended", response_model=list[DiscoveredSourceResponse])
async def list_recommended_sources(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get sources recommended for activation.

    These are sources the system has seen referenced frequently
    across multiple signals with high relevance scores.
    """
    result = await db.execute(
        _visible_sources_query(auth)
        .where(DiscoveredSource.status == "recommended")
        .order_by(DiscoveredSource.relevance_score.desc())
        .limit(limit)
    )
    sources = result.scalars().all()

    return [
        DiscoveredSourceResponse(
            id=str(s.id),
            url=s.url,
            domain=s.domain,
            name=s.name,
            source_type=s.source_type,
            signal_type=s.signal_type,
            mention_count=s.mention_count,
            relevance_score=round(s.relevance_score, 3),
            status=s.status,
            activated_contract_id=str(s.activated_contract_id)
            if s.activated_contract_id
            else None,
            created_at=s.created_at.isoformat() if s.created_at else "",
            last_seen_at=s.last_seen_at.isoformat() if s.last_seen_at else "",
        )
        for s in sources
    ]


@router.get("/stats", response_model=DiscoveredSourceStatsResponse)
async def get_discovery_stats(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    """Get aggregate statistics on source discovery activity."""
    result = await db.execute(
        select(
            DiscoveredSource.status,
            func.count(DiscoveredSource.id).label("cnt"),
        )
        .select_from(DiscoveredSource)
        .outerjoin(Signal, Signal.id == DiscoveredSource.first_seen_signal_id)
        .where(or_(Signal.org_id.is_(None), Signal.org_id == auth.org_id))
        .group_by(DiscoveredSource.status)
    )
    counts: dict[str, int] = {row.status: row.cnt for row in result.all()}
    total = sum(counts.values())
    return DiscoveredSourceStatsResponse(
        discovered=counts.get("discovered", 0),
        recommended=counts.get("recommended", 0),
        activated=counts.get("activated", 0),
        dismissed=counts.get("dismissed", 0),
        total=total,
    )


@router.post("/{source_id}/activate", response_model=ActivateSourceResponse)
async def activate_source(
    source_id: UUID,
    body: ActivateSourceRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Activate a discovered source as a real signal contract.

    Creates a fully functional SignalContract with proper source_url,
    extraction config, and refresh schedule. Requires admin role.
    """
    visible_source = await db.execute(
        _visible_sources_query(auth).where(DiscoveredSource.id == source_id)
    )
    if visible_source.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=404,
            detail="Source not found or inaccessible",
        )

    service = SourceDiscoveryService(db)
    contract = await service.activate_source(
        source_id,
        industry_id=UUID(body.industry_id),
        org_id=auth.org_id,
        name=body.name,
        description=body.description,
    )

    if not contract:
        raise HTTPException(
            status_code=404,
            detail="Source not found or already activated",
        )

    await db.commit()

    return ActivateSourceResponse(
        source_id=str(source_id),
        contract_id=str(contract.id),
        contract_name=contract.name,
        source_url=contract.source_url,
        source_type=contract.source_type,
        schedule_tier=contract.schedule_tier,
        message=f"Source activated. Contract '{contract.name}' will start fetching on a {contract.schedule_tier} schedule.",
    )


@router.post("/{source_id}/dismiss", status_code=200)
async def dismiss_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_permissions(["admin"])),
):
    """Dismiss a discovered source (won't be recommended again). Requires admin role."""
    visible_source = await db.execute(
        _visible_sources_query(auth).where(DiscoveredSource.id == source_id)
    )
    if visible_source.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Source not found")

    service = SourceDiscoveryService(db)
    dismissed = await service.dismiss_source(source_id)

    if not dismissed:
        raise HTTPException(status_code=404, detail="Source not found")

    await db.commit()
    return {"status": "dismissed", "source_id": str(source_id)}
