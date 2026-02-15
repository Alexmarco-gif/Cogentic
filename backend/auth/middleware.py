"""
JWT verification middleware for FastAPI.

Validates JWT tokens and extracts authentication context.
"""

import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.auth import utils as auth_utils
from backend.auth.exceptions import AuthError, ForbiddenError

logger = logging.getLogger(__name__)


class JWTMiddleware(BaseHTTPMiddleware):
    """
    Middleware for JWT token verification.

    For protected routes, verifies JWT signature and claims.
    Attaches token info to request state for use in dependencies.

    Public routes (/, /health, /docs) skip verification.
    """

    # Routes that don't require authentication
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        # /metrics endpoint requires authentication for security
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and verify JWT if needed.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response from handler or error response
        """
        # Skip auth for public paths
        if request.url.path in self.PUBLIC_PATHS or request.url.path.startswith(
            "/webhooks"
        ):
            return await call_next(request)

        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # For API routes, require authentication
        # But first check if this is a known route - if not, let FastAPI return 404
        if not request.url.path.startswith("/api/"):
            # Non-API routes that aren't public - let them through
            # This allows 404s for non-existent routes like /debug, /nonexistent
            return await call_next(request)

        try:
            # Extract and verify token
            token = auth_utils.extract_token_from_header(request)
            payload = await auth_utils.verify_token(token)

            # Attach to request state for dependencies
            request.state.token_payload = payload
            request.state.raw_token = token

            logger.debug(f"Request authenticated for user: {payload.sub}")

        except AuthError as e:
            # Auth failed - return 401 with generic message
            logger.warning(
                f"Authentication failed for {request.url.path}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error": e.message,
                    "details": e.details,
                    "ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("User-Agent"),
                },
            )

            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "message": "Invalid or expired authentication token",
                },
            )

        except Exception as e:
            # Unexpected error - log and return 500
            logger.error(
                f"Unexpected auth error: {e}",
                exc_info=True,
                extra={
                    "path": request.url.path,
                    "method": request.method,
                },
            )

            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "Authentication service unavailable",
                },
            )

        # Continue to route handler
        response = await call_next(request)
        return response


async def auth_exception_handler(request: Request, exc: AuthError) -> JSONResponse:
    """
    Global exception handler for AuthError.

    Returns generic 401 error to client, logs details server-side.
    """
    logger.warning(
        f"Authentication error: {exc.message}",
        extra={
            "error": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
            "ip": request.client.host if request.client else None,
        },
    )

    return JSONResponse(
        status_code=401,
        content={
            "error": "Unauthorized",
            "message": "Invalid or expired authentication token",
        },
    )


async def forbidden_exception_handler(
    request: Request, exc: ForbiddenError
) -> JSONResponse:
    """
    Global exception handler for ForbiddenError.

    Returns 403 error with generic message.
    """
    logger.warning(
        f"Authorization error: {exc.message}",
        extra={
            "error": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
            "ip": request.client.host if request.client else None,
        },
    )

    return JSONResponse(
        status_code=403, content={"error": "Forbidden", "message": "Access denied"}
    )
