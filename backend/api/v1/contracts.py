"""Signal Contracts API endpoints.

CRUD for signal contracts + manual fetch trigger.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.guards import require_role
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.middleware.feature_gating import require_feature
from backend.queue import enqueue_job
from backend.repositories.signal_contract import SignalContractRepository
from backend.schemas.signals import (
    SignalContractCreate,
    SignalContractListResponse,
    SignalContractResponse,
    SignalContractUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contracts")


@router.get("", response_model=SignalContractListResponse)
async def list_contracts(
    industry_id: UUID | None = Query(None, description="Filter by industry"),
    source_type: str | None = Query(None, description="Filter by source type"),
    active_only: bool = Query(True, description="Only active contracts"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List signal contracts with optional filtering."""
    repo = SignalContractRepository(db)

    if industry_id:
        items = await repo.get_by_industry(
            industry_id, active_only=active_only, skip=skip, limit=limit
        )
    elif source_type:
        items = await repo.get_by_source_type(
            source_type, active_only=active_only, skip=skip, limit=limit
        )
    else:
        if active_only:
            items = await repo.get_active_contracts(skip=skip, limit=limit)
        else:
            items = await repo.get_multi(skip=skip, limit=limit)

    total = await repo.count()
    return SignalContractListResponse(
        items=[SignalContractResponse.model_validate(c) for c in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/degraded", response_model=list[SignalContractResponse])
async def list_degraded_contracts(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all degraded contracts (needing attention)."""
    repo = SignalContractRepository(db)
    contracts = await repo.get_degraded_contracts()
    return [SignalContractResponse.model_validate(c) for c in contracts]


@router.get("/{contract_id}", response_model=SignalContractResponse)
async def get_contract(
    contract_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single signal contract by ID."""
    repo = SignalContractRepository(db)
    contract = await repo.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return SignalContractResponse.model_validate(contract)


@router.post("", response_model=SignalContractResponse, status_code=201)
async def create_contract(
    body: SignalContractCreate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _feature_check: bool = Depends(require_feature("custom_contracts")),
):
    """Create a new signal contract. Requires admin role and Mid-Market tier or higher."""
    require_role(auth, "admin")
    repo = SignalContractRepository(db)
    contract = await repo.create(**body.model_dump())
    return SignalContractResponse.model_validate(contract)


@router.patch("/{contract_id}", response_model=SignalContractResponse)
async def update_contract(
    contract_id: UUID,
    body: SignalContractUpdate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing signal contract. Requires admin or owner role."""
    require_role(auth, "admin")
    repo = SignalContractRepository(db)
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    contract = await repo.update(contract_id, **update_data)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return SignalContractResponse.model_validate(contract)


@router.delete("/{contract_id}", status_code=204)
async def delete_contract(
    contract_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a signal contract. Requires admin or owner role."""
    require_role(auth, "admin")
    repo = SignalContractRepository(db)
    deleted = await repo.delete(contract_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contract not found")


@router.post("/{contract_id}/fetch")
async def trigger_fetch(
    contract_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a fetch for a specific contract.

    Enqueues an RQ job — does not block the request.
    Requires admin or owner role.
    """
    require_role(auth, "admin")
    repo = SignalContractRepository(db)
    contract = await repo.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if not contract.is_active:
        raise HTTPException(status_code=400, detail="Contract is inactive")

    from backend.jobs.acquisition_job import fetch_single_contract

    job = enqueue_job(
        fetch_single_contract,
        str(contract_id),
        queue_name="high",
        job_timeout="5m",
    )
    return {
        "status": "queued",
        "job_id": job.id,
        "contract_id": str(contract_id),
        "contract_name": contract.name,
    }


@router.post("/{contract_id}/activate", response_model=SignalContractResponse)
async def activate_contract(
    contract_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Activate a signal contract. Requires admin or owner role."""
    require_role(auth, "admin")
    repo = SignalContractRepository(db)
    contract = await repo.update(
        contract_id, is_active=True, status="active", failure_count=0
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return SignalContractResponse.model_validate(contract)


@router.post("/{contract_id}/deactivate", response_model=SignalContractResponse)
async def deactivate_contract(
    contract_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a signal contract. Requires admin or owner role."""
    require_role(auth, "admin")
    repo = SignalContractRepository(db)
    contract = await repo.update(contract_id, is_active=False, status="disabled")
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return SignalContractResponse.model_validate(contract)
