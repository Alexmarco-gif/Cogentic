"""Paystack webhook handlers."""

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.paystack_service import PaystackError, PaystackService

router = APIRouter(prefix="/webhooks/paystack")


@router.post("")
@router.post("/events")
async def paystack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Receive and process Paystack billing webhooks."""
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    service = PaystackService(db)
    if not service.verify_webhook_signature(raw_body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Paystack signature",
        )

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        ) from exc

    try:
        result = await service.process_webhook_event(payload)
    except PaystackError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {"status": "ok", "result": result}
