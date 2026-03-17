"""Repository for persistent in-app notifications."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.notification import Notification


class NotificationRepository:
    """CRUD operations for the notifications table."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert_by_source(
        self,
        *,
        org_id: UUID,
        type: str,
        title: str,
        body: str,
        source_type: str,
        source_id: str,
    ) -> Notification:
        """Create a notification or return the existing one for the same source.

        Uses source_type + source_id + org_id as a natural key so that
        re-synthesising notifications on repeated calls does not produce
        duplicate rows.
        """
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.org_id == org_id,
                    Notification.source_type == source_type,
                    Notification.source_id == source_id,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        notification = Notification(
            id=uuid4(),
            org_id=org_id,
            type=type,
            title=title,
            body=body,
            source_type=source_type,
            source_id=source_id,
        )
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def list_for_org(
        self,
        org_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        """Return notifications for an organisation, newest first."""
        result = await self.db.execute(
            select(Notification)
            .where(Notification.org_id == org_id)
            .order_by(desc(Notification.created_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get(self, notification_id: UUID) -> Notification | None:
        return await self.db.get(Notification, notification_id)

    async def mark_read(self, notification_id: UUID, org_id: UUID) -> bool:
        """Mark a single notification as read.  Returns True if updated."""
        now = datetime.now(timezone.utc)
        result: CursorResult = await self.db.execute(  # type: ignore[assignment]
            update(Notification)
            .where(
                and_(
                    Notification.id == notification_id,
                    Notification.org_id == org_id,
                    Notification.read_at.is_(None),
                )
            )
            .values(read_at=now)
        )
        return result.rowcount > 0

    async def mark_all_read(self, org_id: UUID) -> int:
        """Mark all unread notifications for an org as read.  Returns count updated."""
        now = datetime.now(timezone.utc)
        result: CursorResult = await self.db.execute(  # type: ignore[assignment]
            update(Notification)
            .where(
                and_(
                    Notification.org_id == org_id,
                    Notification.read_at.is_(None),
                )
            )
            .values(read_at=now)
        )
        return result.rowcount
