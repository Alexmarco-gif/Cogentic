"""Credit balance and transaction API endpoints"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import AuthContext, get_current_user
from backend.database import get_db
from backend.middleware.feature_gating import get_current_organization
from backend.models.organization import Organization
from backend.services.credit_service import CreditService

router = APIRouter(prefix="/credits")


class CreditBalanceResponse(BaseModel):
    """Credit balance response"""

    allocated: int
    consumed: int
    remaining: int
    overage: int
    overage_rate: float
    strict_prepaid_enabled: bool = True


class CreditTransactionResponse(BaseModel):
    """Credit transaction response"""

    id: str
    action_type: str
    credits_consumed: int
    credits_remaining: int
    created_at: str
    metadata: dict | None


class CreditTransactionsResponse(BaseModel):
    """Credit transactions list response"""

    transactions: list[CreditTransactionResponse]
    total: int


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current credit balance for authenticated organization.

    Returns allocated, consumed, remaining credits and overage details.
    """
    credit_service = CreditService(db)
    balance = await credit_service.get_credit_balance(organization.id)

    return CreditBalanceResponse(**balance)


@router.get("/transactions", response_model=CreditTransactionsResponse)
async def get_credit_transactions(
    organization: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Get credit transaction history for authenticated organization.

    Returns recent credit consumption transactions.
    """
    credit_service = CreditService(db)
    transactions = await credit_service.get_transaction_history(organization.id, limit)

    transaction_list = [
        CreditTransactionResponse(
            id=str(txn.id),
            action_type=txn.action_type,
            credits_consumed=txn.credits_consumed,
            credits_remaining=txn.credits_remaining,
            created_at=txn.created_at.isoformat(),
            metadata=txn.transaction_metadata,
        )
        for txn in transactions
    ]

    return CreditTransactionsResponse(
        transactions=transaction_list, total=len(transaction_list)
    )


@router.get("/costs")
async def get_credit_costs(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get credit costs for various actions.

    Requires authentication.
    """
    credit_service = CreditService(db)

    return {
        "credit_costs": credit_service.CREDIT_COSTS,
        "description": "Credits consumed per action type",
    }
