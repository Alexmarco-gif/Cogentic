"""
Database query audit logging for security and compliance.

Logs all database operations with user, org, and resource context.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class QueryAuditLogger:
    """Audit logger for database queries"""

    @staticmethod
    def log_query(
        *,
        user_id: UUID | None,
        org_id: UUID | None,
        table: str,
        action: str,
        filters: Dict[str, Any] | None = None,
        result_count: int | None = None,
        duration_ms: float | None = None,
        request_id: str | None = None,
        resource_ids: list[UUID] | None = None,
    ) -> None:
        """
        Log a database query for audit trail.

        Args:
            user_id: User performing the query (from AuthContext)
            org_id: Organization context
            table: Database table name
            action: Query action (list, get, create, update, delete, count)
            filters: Query filters applied
            result_count: Number of records returned
            duration_ms: Query execution time in milliseconds
            request_id: X-Request-ID from HTTP request
            resource_ids: IDs of resources accessed/modified
        """
        audit_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": str(user_id) if user_id else None,
            "org_id": str(org_id) if org_id else None,
            "table": table,
            "action": action,
            "request_id": request_id,
        }

        if filters:
            audit_data["filters"] = {
                k: str(v) if isinstance(v, UUID) else v for k, v in filters.items()
            }

        if result_count is not None:
            audit_data["result_count"] = result_count

        if duration_ms is not None:
            audit_data["duration_ms"] = round(duration_ms, 2)

        if resource_ids:
            audit_data["resource_ids"] = [str(rid) for rid in resource_ids]

        logger.info(
            f"DB_QUERY | table={table} action={action} org_id={org_id} user_id={user_id}",
            extra={"audit": audit_data},
        )

    @staticmethod
    def log_cross_org_attempt(
        *,
        user_id: UUID,
        user_org_id: UUID,
        attempted_org_id: UUID,
        table: str,
        action: str,
        resource_id: UUID | None = None,
        request_id: str | None = None,
    ) -> None:
        """
        Log attempted cross-org access (security violation).

        Args:
            user_id: User who attempted access
            user_org_id: User's actual org
            attempted_org_id: Org they tried to access
            table: Table they tried to access
            action: Action they attempted
            resource_id: Specific resource ID (if applicable)
            request_id: X-Request-ID
        """
        logger.warning(
            f"CROSS_ORG_ATTEMPT | user={user_id} user_org={user_org_id} "
            f"attempted_org={attempted_org_id} table={table} action={action}",
            extra={
                "security_event": {
                    "type": "cross_org_access_attempt",
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": str(user_id),
                    "user_org_id": str(user_org_id),
                    "attempted_org_id": str(attempted_org_id),
                    "table": table,
                    "action": action,
                    "resource_id": str(resource_id) if resource_id else None,
                    "request_id": request_id,
                }
            },
        )

    @staticmethod
    def log_missing_org_context(
        *,
        table: str,
        action: str,
        user_id: UUID | None = None,
        request_id: str | None = None,
    ) -> None:
        """
        Log query on multi-tenant table without org_id (security violation).

        Args:
            table: Table name
            action: Action attempted
            user_id: User (if available)
            request_id: X-Request-ID
        """
        logger.error(
            f"MISSING_ORG_CONTEXT | table={table} action={action} user={user_id}",
            extra={
                "security_event": {
                    "type": "missing_org_context",
                    "timestamp": datetime.utcnow().isoformat(),
                    "table": table,
                    "action": action,
                    "user_id": str(user_id) if user_id else None,
                    "request_id": request_id,
                }
            },
        )


# Convenience singleton
audit_logger = QueryAuditLogger()
