"""
Health check endpoints.

Provides system health status with optional authentication checks.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends

from backend.auth import AuthContext, get_optional_user

router = APIRouter(prefix="/health")


@router.get("")
async def health_check() -> dict[str, Any]:
    """
    Basic health check (no auth required). Used by load balancers.

    For detailed system health with SLO/cache/circuit-breaker stats,
    use GET /monitoring/health (admin-only).
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "cogent-api",
        "version": "1.0.0",
    }


@router.get("/auth")
async def health_check_with_auth(
    auth: AuthContext = Depends(get_optional_user),
) -> dict[str, Any]:
    """
    Health check with optional authentication info.

    If authenticated, returns user context. Otherwise, returns basic health status.
    Useful for debugging auth issues without requiring authentication.
    """
    response = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "cogent-api",
        "version": "1.0.0",
    }

    if auth:
        response["authenticated"] = "true"
        response["user_id"] = str(auth.user_id)
        response["org_id"] = str(auth.org_id)
        response["role"] = auth.role
    else:
        response["authenticated"] = "false"

    return response
