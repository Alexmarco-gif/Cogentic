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
from backend.job_queue import enqueue_job
from backend.middleware.feature_gating import require_feature
from backend.repositories.signal_contract import SignalContractRepository
from backend.schemas.signals import (
    SignalContractCreate,
    SignalContractListResponse,
    SignalContractResponse,
    SignalContractUpdate,
)
from backend.services.credit_service import CreditService, InsufficientCreditsError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contracts")

_SOURCE_TYPE_PATTERN = r"^(api|scraper|rss|social|webhook)$"


@router.get("", response_model=SignalContractListResponse)
async def list_contracts(
    industry_id: UUID | None = Query(None, description="Filter by industry"),
    source_type: str | None = Query(
        None,
        description="Filter by source type",
        pattern=_SOURCE_TYPE_PATTERN,
    ),
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
            industry_id,
            org_id=auth.org_id,
            active_only=active_only,
            skip=skip,
            limit=limit,
        )
    elif source_type:
        items = await repo.get_by_source_type(
            source_type,
            org_id=auth.org_id,
            active_only=active_only,
            skip=skip,
            limit=limit,
        )
    else:
        if active_only:
            items = await repo.get_active_contracts(
                org_id=auth.org_id,
                skip=skip,
                limit=limit,
            )
        else:
            items = await repo.get_multi(
                skip=skip,
                limit=limit,
                filters={"org_id": auth.org_id},
            )

    total = await repo.count_scoped(
        org_id=auth.org_id,
        industry_id=industry_id,
        source_type=source_type,
        active_only=True if active_only else None,
    )
    return SignalContractListResponse(
        items=[SignalContractResponse.model_validate(c) for c in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/degraded", response_model=list[SignalContractResponse])
async def list_degraded_contracts(
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=200, description="Max records to return"),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all degraded contracts (needing attention)."""
    repo = SignalContractRepository(db)
    contracts = await repo.get_degraded_contracts(
        org_id=auth.org_id,
        skip=skip,
        limit=limit,
    )
    return [SignalContractResponse.model_validate(c) for c in contracts]


@router.get("/{contract_id}", response_model=SignalContractResponse)
async def get_contract(
    contract_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single signal contract by ID."""
    repo = SignalContractRepository(db)
    contract = await repo.get_scoped(contract_id, org_id=auth.org_id)
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
    """Create a new signal contract. Requires admin role and Mid-Market tier or higher.

    Consumes 25 credits per contract.
    """
    require_role(auth, "admin")
    credit_service = CreditService(db)
    try:
        await credit_service.consume_credits(
            org_id=auth.org_id,
            user_id=auth.user_id,
            action_type="contract_create",
            credits=25,
            metadata={"contract_name": body.name},
        )
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Insufficient credits to create a contract. "
                f"Requires {e.required} credits and {e.remaining} remain."
            ),
        ) from e
    repo = SignalContractRepository(db)
    contract = await repo.create(**body.model_dump(), org_id=auth.org_id)
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

    existing = await repo.get_scoped(contract_id, org_id=auth.org_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Contract not found")

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
    contract = await repo.get_scoped(contract_id, org_id=auth.org_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
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
    contract = await repo.get_scoped(contract_id, org_id=auth.org_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if not contract.is_active:
        raise HTTPException(status_code=400, detail="Contract is inactive")
    if contract.source_type == "webhook":
        raise HTTPException(
            status_code=400,
            detail=(
                "Webhook contracts are delivery-only and cannot be fetched manually. "
                "Use a pull-based source type for scheduled acquisition."
            ),
        )

    credit_service = CreditService(db)
    try:
        await credit_service.consume_credits(
            org_id=auth.org_id,
            user_id=auth.user_id,
            action_type="contract_manual_fetch",
            credits=25,
            metadata={"contract_id": str(contract_id), "contract_name": contract.name},
        )
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Insufficient credits to trigger a manual fetch. "
                f"Requires {e.required} credits and {e.remaining} remain."
            ),
        ) from e

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
    existing = await repo.get_scoped(contract_id, org_id=auth.org_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Contract not found")
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
    existing = await repo.get_scoped(contract_id, org_id=auth.org_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Contract not found")
    contract = await repo.update(contract_id, is_active=False, status="disabled")
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return SignalContractResponse.model_validate(contract)
