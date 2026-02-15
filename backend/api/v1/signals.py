"""Signals API endpoints.

Browse, filter, search, and query signal catalog.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.repositories.signal import SignalRepository
from backend.schemas.signals import (
    SignalDetailResponse,
    SignalListResponse,
    SignalResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/signals")


@router.get("", response_model=SignalListResponse)
async def list_signals(
    signal_type: str | None = Query(None, description="Filter by type"),
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Browse/filter/search signal catalog."""
    repo = SignalRepository(db)

    if signal_type:
        items = await repo.get_by_type(
            signal_type, min_confidence=min_confidence, skip=skip, limit=limit
        )
    else:
        items = await repo.get_visible(skip=skip, limit=limit)

    total = await repo.count()
    return SignalListResponse(
        items=[SignalResponse.model_validate(s) for s in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/trending", response_model=list[SignalResponse])
async def get_trending_signals(
    limit: int = Query(20, ge=1, le=100),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get ML-ranked trending signals."""
    repo = SignalRepository(db)
    signals = await repo.get_trending(limit=limit)
    return [SignalResponse.model_validate(s) for s in signals]


@router.get("/feed", response_model=SignalListResponse)
async def get_signal_feed(
    industry_id: UUID | None = Query(None),
    signal_type: str | None = Query(None),
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Real-time signal feed (paginated, filterable)."""
    repo = SignalRepository(db)
    items = await repo.get_feed(
        industry_id=industry_id,
        signal_type=signal_type,
        min_confidence=min_confidence,
        skip=skip,
        limit=limit,
    )
    total = await repo.count()
    return SignalListResponse(
        items=[SignalResponse.model_validate(s) for s in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{signal_id}", response_model=SignalDetailResponse)
async def get_signal(
    signal_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get single signal detail + entity links."""
    repo = SignalRepository(db)
    signal = await repo.get(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return SignalDetailResponse.model_validate(signal)


@router.get("/entity/{entity_id}", response_model=SignalListResponse)
async def get_signals_by_entity(
    entity_id: UUID,
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all signals linked to a given entity."""
    repo = SignalRepository(db)
    items = await repo.get_by_entity(
        entity_id, min_confidence=min_confidence, skip=skip, limit=limit
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
    db: AsyncSession = Depends(get_db),
):
    """Get all signals from a specific contract."""
    repo = SignalRepository(db)
    items = await repo.get_by_contract(contract_id, skip=skip, limit=limit)
    total = await repo.count_by_contract(contract_id)
    return SignalListResponse(
        items=[SignalResponse.model_validate(s) for s in items],
        total=total,
        skip=skip,
        limit=limit,
    )
