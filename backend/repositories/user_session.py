"""
Repository for user_sessions table.

Provides upsert-on-request, list, and soft-revoke operations.
Used by get_current_user (via a background task) and by the
/users/me/sessions API endpoints.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user_session import UserSession

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _parse_device(user_agent: str | None) -> str:
    """
    Quick heuristic to turn a raw User-Agent into a readable label.

    Examples:
        "Mozilla/5.0 (Macintosh...) Chrome/123"  → "Chrome on macOS"
        "Mozilla/5.0 (iPhone...) Safari/..."      → "Safari on iPhone"
        None                                       → "Unknown"
    """
    if not user_agent:
        return "Unknown"

    ua = user_agent.lower()

    # OS detection
    if "iphone" in ua:
        os_label = "iPhone"
    elif "ipad" in ua:
        os_label = "iPad"
    elif "android" in ua:
        os_label = "Android"
    elif "macintosh" in ua or "mac os x" in ua:
        os_label = "macOS"
    elif "windows" in ua:
        os_label = "Windows"
    elif "linux" in ua:
        os_label = "Linux"
    else:
        os_label = "Unknown OS"

    # Browser detection (order matters — check Edge/Opera before Chrome)
    if "edg/" in ua or "edge/" in ua:
        browser = "Edge"
    elif "opr/" in ua or "opera" in ua:
        browser = "Opera"
    elif "chrome" in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua:
        browser = "Safari"
    else:
        browser = "Browser"

    return f"{browser} on {os_label}"


class UserSessionRepository:
    """CRUD operations for the user_sessions table."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Write operations ──────────────────────────────────────────────────

    async def upsert_session(
        self,
        user_id: UUID,
        ip_address: str,
        user_agent: str | None = None,
    ) -> None:
        """
        Create a new session or bump last_active_at on the matching one.

        Uniqueness key: (user_id, ip_address, device) — so the same
        browser on the same machine updates a single row rather than
        creating duplicates.
        """
        device = _parse_device(user_agent)
        now = _now_utc()

        try:
            stmt = (
                pg_insert(UserSession)
                .values(
                    user_id=user_id,
                    ip_address=ip_address,
                    device=device,
                    user_agent=user_agent,
                    last_active_at=now,
                    revoked_at=None,
                )
                .on_conflict_do_update(
                    index_elements=None,
                    constraint="uq_user_sessions_user_ip_device",
                    set_={
                        "last_active_at": now,
                        "user_agent": user_agent,
                        "revoked_at": None,  # un-revoke if re-authenticated
                        "updated_at": now,
                    },
                )
            )
            await self.db.execute(stmt)
            await self.db.commit()
        except Exception:
            logger.exception(
                "Failed to upsert user session",
                extra={"user_id": str(user_id), "ip": ip_address},
            )
            await self.db.rollback()

    async def revoke_session(self, session_id: UUID, user_id: UUID) -> bool:
        """
        Soft-revoke a session.  Returns True if a row was affected.
        Only revokes sessions belonging to the requesting user.
        """
        result: CursorResult = await self.db.execute(  # type: ignore[assignment]
            update(UserSession)
            .where(
                and_(
                    UserSession.id == session_id,
                    UserSession.user_id == user_id,
                    UserSession.revoked_at.is_(None),
                )
            )
            .values(revoked_at=_now_utc())
        )
        await self.db.commit()
        return result.rowcount > 0

    async def revoke_all_other_sessions(
        self, user_id: UUID, current_ip: str, current_device: str
    ) -> int:
        """Revoke all sessions except the one matching ip + device."""
        result: CursorResult = await self.db.execute(  # type: ignore[assignment]
            update(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.revoked_at.is_(None),
                    ~and_(
                        UserSession.ip_address == current_ip,
                        UserSession.device == current_device,
                    ),
                )
            )
            .values(revoked_at=_now_utc())
        )
        await self.db.commit()
        return result.rowcount

    # ── Read operations ───────────────────────────────────────────────────

    async def list_active_sessions(self, user_id: UUID) -> list[UserSession]:
        """Return all non-revoked sessions, newest first."""
        result = await self.db.execute(
            select(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.revoked_at.is_(None),
                )
            )
            .order_by(UserSession.last_active_at.desc())
        )
        return list(result.scalars().all())

    async def get_session(self, session_id: UUID, user_id: UUID) -> UserSession | None:
        result = await self.db.execute(
            select(UserSession).where(
                and_(
                    UserSession.id == session_id,
                    UserSession.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    # ── Cleanup ──────────────────────────────────────────────────────────

    async def purge_old_revoked(self, older_than_days: int = 30) -> int:
        """Delete revoked sessions older than N days. For scheduled cleanup."""
        from datetime import timedelta

        cutoff = _now_utc() - timedelta(days=older_than_days)
        result: CursorResult = await self.db.execute(  # type: ignore[assignment]
            delete(UserSession).where(
                and_(
                    UserSession.revoked_at.is_not(None),
                    UserSession.revoked_at < cutoff,
                )
            )
        )
        await self.db.commit()
        return result.rowcount
