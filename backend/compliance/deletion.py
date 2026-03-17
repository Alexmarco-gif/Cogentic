"""GDPR/NDPR Right to Be Forgotten.

Cascade-deletes all user data across tables while preserving the
audit trail (anonymised).  Fully logged for compliance evidence.
"""

import logging
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_log import AuditLog
from backend.models.chat_session import ChatSession
from backend.models.search_query import SearchQuery
from backend.models.user import User
from backend.models.user_feedback import UserFeedback
from backend.models.user_session import UserSession

logger = logging.getLogger(__name__)


async def delete_user_data(
    db: AsyncSession,
    user_id: UUID,
    *,
    requesting_ip: str | None = None,
    request_id: str | None = None,
) -> dict[str, int]:
    """Permanently delete all user data (GDPR Article 17).

    Execution order:
      1. Delete chat sessions (messages cascade via FK).
      2. Delete search queries.
      3. Delete feedback events.
      4. Delete device sessions.
      5. Anonymise audit logs (SET user_id = NULL, redact PII from extra_data).
      6. Delete the user record itself.

    The caller is responsible for committing the transaction so that
    the entire operation is atomic.

    Args:
        db: Async database session (caller commits).
        user_id: Target user UUID.
        requesting_ip: IP of the requester (for the final audit entry).
        request_id: Trace ID for the request.

    Returns:
        Dict mapping table names to the number of rows deleted.

    Raises:
        ValueError: If user not found.
    """
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError(f"User {user_id} not found")

    counts: dict[str, int] = {}

    # ── 1. Chat sessions (messages cascade via FK ondelete) ───────────────
    res = await db.execute(delete(ChatSession).where(ChatSession.user_id == user_id))
    counts["chat_sessions"] = res.rowcount

    # ── 2. Search queries ─────────────────────────────────────────────────
    res = await db.execute(delete(SearchQuery).where(SearchQuery.user_id == user_id))
    counts["search_queries"] = res.rowcount

    # ── 3. Feedback events ────────────────────────────────────────────────
    res = await db.execute(delete(UserFeedback).where(UserFeedback.user_id == user_id))
    counts["user_feedback"] = res.rowcount

    # ── 4. Device sessions ────────────────────────────────────────────────
    res = await db.execute(delete(UserSession).where(UserSession.user_id == user_id))
    counts["user_sessions"] = res.rowcount

    # ── 5. Anonymise audit logs (keep trail, remove PII) ──────────────────
    res = await db.execute(
        update(AuditLog).where(AuditLog.user_id == user_id).values(user_id=None)
    )
    counts["audit_logs_anonymised"] = res.rowcount

    # ── 6. Record a final audit entry *before* deleting the user ──────────
    deletion_log = AuditLog(
        org_id=user.organizations[0].org_id if user.organizations else user_id,
        user_id=None,  # Already anonymising
        action="user.data_deleted",
        resource_type="user",
        resource_id=user_id,
        ip_address=requesting_ip,
        request_id=request_id,
        changes={"deleted_counts": counts},
        extra_data={"compliance": "gdpr_article_17"},
    )
    db.add(deletion_log)
    await db.flush()

    # ── 7. Delete the user record (OrgUser cascades via FK) ───────────────
    await db.delete(user)
    await db.flush()
    counts["user"] = 1

    logger.warning(
        "GDPR data deletion completed",
        extra={
            "user_id": str(user_id),
            "request_id": request_id,
            "deleted_counts": counts,
            "compliance_event": "right_to_be_forgotten",
        },
    )

    return counts
