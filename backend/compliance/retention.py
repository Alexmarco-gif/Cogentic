"""Data Retention Policy — automatic data aging.

Enforces the retention periods defined in ``data_classification.py``
by deleting records that have exceeded their classification-specific TTL.

Designed to run as a periodic job (e.g. daily cron via the worker).
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.compliance.data_classification import (
    MODEL_CLASSIFICATIONS,
    DataClassification,
    DataPolicy,
)
from backend.models.chat_session import ChatSession
from backend.models.search_query import SearchQuery
from backend.models.user_feedback import UserFeedback
from backend.models.user_session import UserSession

logger = logging.getLogger(__name__)

# Map model names to their SQLAlchemy classes and timestamp column.
_RETENTION_TARGETS: list[tuple[str, type, str]] = [
    ("ChatSession", ChatSession, "created_at"),
    ("SearchQuery", SearchQuery, "created_at"),
    ("UserFeedback", UserFeedback, "created_at"),
    ("UserSession", UserSession, "last_active_at"),
]


async def enforce_retention(db: AsyncSession) -> dict[str, int]:
    """Delete records that exceed their classification retention period.

    Iterates over every table registered in ``_RETENTION_TARGETS``,
    looks up its data classification, calculates the cutoff date,
    and hard-deletes expired rows.

    The caller is responsible for committing the transaction.

    Returns:
        Dict mapping model name to the number of rows deleted.
    """
    now = datetime.now(timezone.utc)
    results: dict[str, int] = {}

    for model_name, model_cls, ts_column in _RETENTION_TARGETS:
        classification = MODEL_CLASSIFICATIONS.get(
            model_name, DataClassification.INTERNAL
        )
        retention_days = DataPolicy.get_retention_days(classification)
        cutoff = now - timedelta(days=retention_days)

        col = getattr(model_cls, ts_column, None)
        if col is None:
            logger.warning(f"Retention skip: {model_name} has no column '{ts_column}'")
            continue

        res = await db.execute(delete(model_cls).where(col < cutoff))
        deleted = res.rowcount
        results[model_name] = deleted

        if deleted > 0:
            logger.info(
                f"Retention: deleted {deleted} {model_name} rows "
                f"older than {retention_days}d (cutoff={cutoff.isoformat()})",
                extra={
                    "model": model_name,
                    "classification": classification.value,
                    "retention_days": retention_days,
                    "deleted_count": deleted,
                },
            )

    logger.info(
        "Data retention enforcement complete",
        extra={"results": results},
    )

    return results
