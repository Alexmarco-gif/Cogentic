"""GDPR/NDPR Consent Management.

Records, tracks, and manages user consent preferences.
All changes are audit-logged for compliance evidence.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_log import AuditLog
from backend.models.user import User

logger = logging.getLogger(__name__)


class ConsentType(str, Enum):
    """Types of consent a user can grant or withdraw."""

    DATA_PROCESSING = "data_processing"  # Core GDPR consent
    MARKETING = "marketing"  # Marketing communications
    ANALYTICS = "analytics"  # Product analytics / PostHog
    AI_TRAINING = "ai_training"  # Use data for model improvement


async def record_consent(
    db: AsyncSession,
    user_id: UUID,
    consent_type: ConsentType,
    granted: bool,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Record a user consent decision.

    Updates the user record for the primary ``data_processing`` consent
    and creates an audit log entry for every consent change so that
    a full history is available for regulatory inspections.

    Args:
        db: Async database session (caller commits).
        user_id: Target user UUID.
        consent_type: Which category of consent.
        granted: True = consent given, False = withdrawn.
        ip_address: Requester IP for audit trail.
        user_agent: Requester User-Agent for audit trail.
        request_id: Trace ID.

    Returns:
        Dict with the recorded consent state.

    Raises:
        ValueError: If user not found.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError(f"User {user_id} not found")

    now = datetime.now(timezone.utc)
    action = "consent.granted" if granted else "consent.withdrawn"

    # Update the primary consent flag on the user record
    if consent_type == ConsentType.DATA_PROCESSING:
        previous = user.data_processing_consent
        user.data_processing_consent = granted
        user.consent_date = now if granted else None
        changes = {
            "before": {"data_processing_consent": previous},
            "after": {"data_processing_consent": granted},
        }
    else:
        # Other consent types are tracked only via audit logs
        changes = {"consent_type": consent_type.value, "granted": granted}

    await db.flush()

    # Audit log entry
    org_id = user.organizations[0].org_id if user.organizations else user_id
    audit = AuditLog(
        org_id=org_id,
        user_id=user_id,
        action=action,
        resource_type="consent",
        resource_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
        changes=changes,
        extra_data={
            "consent_type": consent_type.value,
            "granted": granted,
            "compliance": "gdpr_article_7",
        },
    )
    db.add(audit)
    await db.flush()

    logger.info(
        f"Consent {action}: {consent_type.value}",
        extra={
            "user_id": str(user_id),
            "consent_type": consent_type.value,
            "granted": granted,
            "request_id": request_id,
        },
    )

    return {
        "user_id": str(user_id),
        "consent_type": consent_type.value,
        "granted": granted,
        "recorded_at": now.isoformat(),
    }


async def get_consent_history(
    db: AsyncSession,
    user_id: UUID,
) -> list[dict[str, Any]]:
    """Retrieve full consent change history from audit logs.

    Args:
        db: Async database session.
        user_id: Target user UUID.

    Returns:
        List of consent events ordered oldest-first.
    """
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.resource_type == "consent",
            AuditLog.resource_id == user_id,
        )
        .order_by(AuditLog.created_at)
    )
    logs = result.scalars().all()

    return [
        {
            "action": log.action,
            "consent_type": (log.extra_data or {}).get("consent_type"),
            "granted": (log.extra_data or {}).get("granted"),
            "ip_address": log.ip_address,
            "recorded_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
