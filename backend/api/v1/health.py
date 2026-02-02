"""
Health check endpoints.

Provides system health status with optional authentication checks.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from datetime import datetime

from backend.auth import get_optional_user, AuthContext

router = APIRouter(prefix="/health")


@router.get("")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint (no authentication required).

    Returns:
        System health status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "cogent-api",
        "version": "1.0.0",
    }


@router.get("/auth")
async def health_check_with_auth(
    auth: AuthContext = Depends(get_optional_user),
) -> Dict[str, Any]:
    """
    Health check with optional authentication info.

    If authenticated, returns user context. Otherwise, returns basic health status.
    Useful for debugging auth issues without requiring authentication.
    """
    response = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
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
