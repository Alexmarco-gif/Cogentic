"""
Auth0 webhook handlers.

Handles Auth0 events for user lifecycle management:
- User signup (create user + personal org)
- User login (update stats)
- User deletion (cascade delete)

Security:
- Webhook signature verification (HMAC SHA256)
- Idempotency via Redis (prevent duplicate processing)
- No authentication required (webhook secret verifies source)
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import get_db
from backend.redis_client import get_redis
from backend.repositories.organization import OrganizationRepository
from backend.repositories.user import UserRepository

router = APIRouter(prefix="/webhooks/auth0")


class Auth0WebhookEvent(BaseModel):
    """Auth0 webhook event payload"""

    event: str = Field(
        ...,
        description="Event type (post-login, post-registration, post-user-deletion)",
    )
    user_id: str = Field(..., description="Auth0 user ID")
    email: str | None = None
    name: str | None = None
    picture: str | None = None
    created_at: str | None = None


async def verify_webhook_signature(request: Request) -> bool:
    """
    Verify Auth0 webhook signature using HMAC SHA256.

    Auth0 sends signature in X-Auth0-Signature header.
    Format: sha256=<hex_signature>

    Args:
        request: FastAPI request with headers and body

    Returns:
        True if signature is valid

    Raises:
        HTTPException: If signature is missing or invalid
    """
    signature_header = request.headers.get("X-Auth0-Signature")
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature"
        )

    # Parse signature header (format: sha256=<hex>)
    try:
        algorithm, signature = signature_header.split("=", 1)
        if algorithm != "sha256":
            raise ValueError("Unsupported signature algorithm")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature format"
        )

    # Get webhook secret from config
    webhook_secret = get_settings().auth0_webhook_secret
    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    # Read request body
    body = await request.body()

    # Compute expected signature
    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

    # Compare signatures (constant-time comparison)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
        )

    return True


async def check_idempotency(event_id: str, ttl_seconds: int = 86400) -> bool:
    """
    Check if event has already been processed (idempotency).

    Uses Redis to store processed event IDs with TTL.

    Args:
        event_id: Unique event identifier
        ttl_seconds: How long to remember processed events (default: 24 hours)

    Returns:
        True if event is new (not processed), False if already processed
    """
    redis = await get_redis()
    key = f"webhook:processed:{event_id}"

    # Try to set key (only succeeds if doesn't exist)
    was_set = await redis.set(key, "1", ex=ttl_seconds, nx=True)

    return was_set is not None


async def handle_user_signup(
    user_id: str,
    email: str,
    name: str | None,
    picture: str | None,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Handle user signup event from Auth0.

    Creates:
    1. User record in database
    2. Personal organization for the user
    3. OrgUser membership with owner role

    Args:
        user_id: Auth0 user ID (e.g., "auth0|abc123")
        email: User email
        name: User display name
        picture: User profile picture URL
        db: Database session

    Returns:
        Dict with created user_id and org_id
    """
    user_repo = UserRepository(db)
    org_repo = OrganizationRepository(db, user_id=None, request_id=None)

    # Check if user already exists (idempotency at DB level)
    existing_user = await user_repo.get_by_auth0_id(user_id)
    if existing_user:
        return {
            "status": "already_exists",
            "user_id": str(existing_user.id),
            "message": "User already exists",
        }

    # Create user
    user = await user_repo.create(
        auth0_id=user_id,
        email=email,
        name=name,
        picture_url=picture,
        last_login_at=datetime.now(timezone.utc),
        login_count=1,
    )

    # Generate org slug from email (e.g., "user-abc123" from "user@example.com")
    email_prefix = email.split("@")[0].lower()
    base_slug = f"{email_prefix}-{str(uuid4())[:8]}"

    # Ensure slug is unique
    slug = base_slug
    counter = 1
    while await org_repo.slug_exists(slug):
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Create personal organization
    org = await org_repo.create(
        name=f"{name or email}'s Organization",
        slug=slug,
        billing_email=email,
    )

    # Create organization membership (owner role)
    await org_repo.add_member(org.id, user.id, role="owner")

    await db.commit()

    return {
        "status": "created",
        "user_id": str(user.id),
        "org_id": str(org.id),
        "message": "User and organization created successfully",
    }


async def handle_user_login(
    user_id: str,
    email: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Handle user login event from Auth0.

    Updates:
    - last_login_at timestamp
    - login_count increment

    Args:
        user_id: Auth0 user ID
        email: User email (for logging)
        db: Database session

    Returns:
        Dict with update status
    """
    user_repo = UserRepository(db)

    user = await user_repo.get_by_auth0_id(user_id)
    if not user:
        # User doesn't exist yet - might be first login
        # Return success but log warning
        _redacted = email[:2] + "***" if email else "<unknown>"
        return {
            "status": "user_not_found",
            "message": f"User {_redacted} not found in database",
        }

    # Update login stats
    await user_repo.update(
        user.id,
        last_login_at=datetime.now(timezone.utc),
        login_count=user.login_count + 1,
    )

    await db.commit()

    return {
        "status": "updated",
        "user_id": str(user.id),
        "login_count": user.login_count + 1,
        "message": "Login stats updated",
    }


async def handle_user_deletion(
    user_id: str,
    email: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Handle user deletion event from Auth0.

    Soft deletes:
    - User record
    - User's personal organization (if they're the only owner)
    - Organization memberships

    Args:
        user_id: Auth0 user ID
        email: User email
        db: Database session

    Returns:
        Dict with deletion status
    """
    user_repo = UserRepository(db)

    user = await user_repo.get_by_auth0_id(user_id)
    if not user:
        _redacted = email[:2] + "***" if email else "<unknown>"
        return {
            "status": "not_found",
            "message": f"User {_redacted} not found in database",
        }

    # Soft delete user (SQLAlchemy will cascade to org_users via relationship)
    await user_repo.soft_delete(user.id)

    await db.commit()

    return {
        "status": "deleted",
        "user_id": str(user.id),
        "message": "User soft deleted successfully",
    }


@router.post("")
@router.post("/events")
async def auth0_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Auth0 webhook endpoint.

    Handles Auth0 events:
    - post-registration: Create user and personal org
    - post-login: Update login stats
    - post-user-deletion: Soft delete user

    Security:
    - Verifies webhook signature
    - Implements idempotency via Redis

    Returns:
        200: Event processed successfully
        401: Invalid signature
        409: Event already processed
        500: Processing error
    """
    # Verify webhook signature
    await verify_webhook_signature(request)

    # Parse event payload
    body = await request.body()
    payload = json.loads(body)

    # Extract event data
    event_type = payload.get("event")
    user_id = payload.get("user_id")
    email = payload.get("email", "unknown@example.com")

    # Generate event ID for idempotency
    event_id = f"{event_type}:{user_id}:{payload.get('timestamp', datetime.now(timezone.utc).isoformat())}"
    event_id_hash = hashlib.sha256(event_id.encode()).hexdigest()

    # Check idempotency
    is_new = await check_idempotency(event_id_hash)
    if not is_new:
        return {
            "status": "already_processed",
            "event_id": event_id_hash,
            "message": "Event already processed",
        }

    # Route to appropriate handler
    try:
        if event_type == "post-registration":
            result = await handle_user_signup(
                user_id=user_id,
                email=email,
                name=payload.get("name"),
                picture=payload.get("picture"),
                db=db,
            )
        elif event_type == "post-login":
            result = await handle_user_login(
                user_id=user_id,
                email=email,
                db=db,
            )
        elif event_type == "post-user-deletion":
            result = await handle_user_deletion(
                user_id=user_id,
                email=email,
                db=db,
            )
        else:
            return {
                "status": "ignored",
                "event_type": event_type,
                "message": f"Unknown event type: {event_type}",
            }

        return {
            **result,
            "event_id": event_id_hash,
            "event_type": event_type,
        }

    except Exception:
        # Log error but don't expose details to client
        logger.error("Webhook processing error", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook event",
        )
