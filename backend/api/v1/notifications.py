"""Notifications API endpoint.

Notifications are persisted per-organisation in the ``notifications`` table.
On each ``GET /notifications`` call, recent signals and contract events are
synthesised and written to the table (idempotent upsert), so notifications
accumulate over time and survive across requests.

Endpoints also expose mark-as-read operations.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db
from backend.repositories.notification import NotificationRepository
from backend.repositories.signal import SignalRepository
from backend.repositories.signal_contract import SignalContractRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications")

# ── Response schemas ───────────────────────────────────────────────────────────


class NotificationItem(BaseModel):
    id: str
    type: str  # "signal" | "contract" | "system"
    title: str
    body: str
    created_at: str
    unread: bool


class NotificationsResponse(BaseModel):
    items: list[NotificationItem]
    unread_count: int


class MarkReadResponse(BaseModel):
    updated: int


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _synthesise_and_persist(
    auth: AuthContext,
    signal_repo: SignalRepository,
    contract_repo: SignalContractRepository,
    notif_repo: NotificationRepository,
) -> None:
    """Synthesise notifications from recent platform events and upsert to DB."""

    try:
        recent_signals = await signal_repo.get_visible(
            org_id=auth.org_id, skip=0, limit=10
        )
        for sig in recent_signals:
            if (sig.confidence or 0) >= 0.75:
                entity = sig.extracted_data.get("entity_name", "Unknown Entity")
                summary = sig.summary or sig.title or "New intelligence signal detected"
                await notif_repo.upsert_by_source(
                    org_id=auth.org_id,
                    type="signal",
                    title="New signal detected",
                    body=f"{entity} — {summary[:100]}",
                    source_type="signal",
                    source_id=str(sig.id),
                )
    except Exception as exc:
        logger.warning("Failed to synthesise signal notifications: %s", exc)

    try:
        active_contracts = await contract_repo.get_active_contracts(
            org_id=auth.org_id,
            skip=0,
            limit=10,
        )
        for contract in active_contracts:
            if contract.failure_count > 0:
                await notif_repo.upsert_by_source(
                    org_id=auth.org_id,
                    type="contract",
                    title="Contract validation warning",
                    body=(
                        f"{contract.name} has {contract.failure_count} "
                        f"schema warning{'s' if contract.failure_count > 1 else ''} — review required"
                    ),
                    source_type="contract",
                    source_id=str(contract.id),
                )
    except Exception as exc:
        logger.warning("Failed to synthesise contract notifications: %s", exc)


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("", response_model=NotificationsResponse)
async def list_notifications(
    limit: int = Query(20, ge=1, le=50),
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationsResponse:
    """Return recent in-app notifications for the authenticated organisation.

    Synthesises new notifications from recent high-confidence signals and
    contract events on every call (idempotent), then reads from the
    persistent ``notifications`` table.
    """
    notif_repo = NotificationRepository(db)
    signal_repo = SignalRepository(db)
    contract_repo = SignalContractRepository(db)

    await _synthesise_and_persist(auth, signal_repo, contract_repo, notif_repo)
    await db.commit()

    rows = await notif_repo.list_for_org(auth.org_id, skip=0, limit=limit)

    cutoff = datetime.now(timezone.utc) - timedelta(days=2)
    items = [
        NotificationItem(
            id=str(row.id),
            type=row.type,
            title=row.title,
            body=row.body,
            created_at=row.created_at.isoformat(),
            unread=row.read_at is None
            and row.created_at.replace(tzinfo=timezone.utc) > cutoff,
        )
        for row in rows
    ]

    unread_count = sum(1 for n in items if n.unread)
    return NotificationsResponse(items=items, unread_count=unread_count)


@router.patch("/{notification_id}/read", response_model=MarkReadResponse)
async def mark_notification_read(
    notification_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarkReadResponse:
    """Mark a single notification as read."""
    notif_repo = NotificationRepository(db)
    updated = await notif_repo.mark_read(notification_id, auth.org_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or already read.",
        )
    await db.commit()
    return MarkReadResponse(updated=1)


@router.post("/mark-all-read", response_model=MarkReadResponse)
async def mark_all_notifications_read(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarkReadResponse:
    """Mark all unread notifications for the authenticated organisation as read."""
    notif_repo = NotificationRepository(db)
    count = await notif_repo.mark_all_read(auth.org_id)
    await db.commit()
    return MarkReadResponse(updated=count)


def _human_age(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return "Just now"
    if total_seconds < 3600:
        mins = total_seconds // 60
        return f"{mins} min ago"
    if total_seconds < 86400:
        hrs = total_seconds // 3600
        return f"{hrs} hr ago"
    days = total_seconds // 86400
    return f"{days} day{'s' if days > 1 else ''} ago"
