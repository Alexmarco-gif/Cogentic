"""GDPR/NDPR/HIPAA Data Portability Export.

Collects all user data across tables, structures it as JSON,
and returns a portable archive for GDPR Article 20 compliance.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.chat_session import ChatSession
from backend.models.search_query import SearchQuery
from backend.models.user import User
from backend.models.user_feedback import UserFeedback
from backend.models.user_session import UserSession

logger = logging.getLogger(__name__)


async def export_user_data(
    db: AsyncSession,
    user_id: UUID,
) -> dict[str, Any]:
    """Collect and structure all user data for GDPR export.

    Gathers data from every table that holds user-owned records:
      - Profile (email, name, picture, consent, timestamps)
      - Chat sessions + messages
      - Search queries (text only — results excluded for size)
      - Feedback events
      - Device sessions (device, IP, timestamps)

    Excludes:
      - Internal IDs (UUIDs converted to strings for readability)
      - API key hashes (security-sensitive)
      - Audit logs (compliance trail — not user-owned data)

    Args:
        db: Async database session.
        user_id: The user whose data to export.

    Returns:
        Structured dict ready for JSON serialisation.

    Raises:
        ValueError: If user not found.
    """
    # ── 1. User profile ───────────────────────────────────────────────────
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError(f"User {user_id} not found")

    profile = {
        "email": user.email,
        "name": user.name,
        "picture_url": user.picture_url,
        "created_at": _iso(user.created_at),
        "last_login_at": _iso(user.last_login_at),
        "login_count": user.login_count,
        "data_processing_consent": user.data_processing_consent,
        "consent_date": _iso(user.consent_date),
    }

    # ── 2. Chat sessions + messages ───────────────────────────────────────
    sessions_result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at)
    )
    sessions = sessions_result.scalars().all()

    chat_sessions = []
    for session in sessions:
        messages = [
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": _iso(msg.created_at),
            }
            for msg in sorted(session.messages, key=lambda m: m.created_at)
        ]
        chat_sessions.append(
            {
                "title": session.title,
                "status": session.status,
                "created_at": _iso(session.created_at),
                "messages": messages,
            }
        )

    # ── 3. Search queries ─────────────────────────────────────────────────
    queries_result = await db.execute(
        select(SearchQuery)
        .where(SearchQuery.user_id == user_id)
        .order_by(SearchQuery.created_at)
    )
    search_queries = [
        {
            "query_text": q.query_text,
            "source_count": q.source_count,
            "response_time_ms": q.response_time_ms,
            "created_at": _iso(q.created_at),
        }
        for q in queries_result.scalars().all()
    ]

    # ── 4. Feedback events ────────────────────────────────────────────────
    feedback_result = await db.execute(
        select(UserFeedback)
        .where(UserFeedback.user_id == user_id)
        .order_by(UserFeedback.created_at)
    )
    feedback = [
        {
            "feedback_type": fb.feedback_type,
            "target_type": fb.target_type,
            "sentiment": fb.sentiment,
            "created_at": _iso(fb.created_at),
        }
        for fb in feedback_result.scalars().all()
    ]

    # ── 5. Device sessions ────────────────────────────────────────────────
    device_sessions_result = await db.execute(
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .order_by(UserSession.created_at)
    )
    device_sessions = [
        {
            "device": s.device,
            "ip_address": s.ip_address,
            "last_active_at": _iso(s.last_active_at),
            "created_at": _iso(s.created_at),
            "revoked_at": _iso(s.revoked_at),
        }
        for s in device_sessions_result.scalars().all()
    ]

    # ── Assemble export ───────────────────────────────────────────────────
    export = {
        "export_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user_id": str(user_id),
        "profile": profile,
        "chat_sessions": chat_sessions,
        "search_queries": search_queries,
        "feedback": feedback,
        "device_sessions": device_sessions,
    }

    logger.info(
        "GDPR data export generated",
        extra={
            "user_id": str(user_id),
            "chat_sessions": len(chat_sessions),
            "search_queries": len(search_queries),
            "feedback_events": len(feedback),
            "device_sessions": len(device_sessions),
        },
    )

    return export


def _iso(dt: datetime | None) -> str | None:
    """Convert datetime to ISO-8601 or None."""
    return dt.isoformat() if dt else None
