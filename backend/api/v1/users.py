"""
User profile endpoints.

Handles user profile retrieval, updates, and privacy/data management.
"""

import logging
import uuid as _uuid
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import AuthContext, get_current_user
from backend.compliance.consent import ConsentType, get_consent_history, record_consent
from backend.compliance.deletion import delete_user_data
from backend.compliance.export import export_user_data
from backend.database import get_db
from backend.redis_client import get_redis
from backend.repositories.organization import OrganizationRepository
from backend.repositories.user import UserRepository
from backend.repositories.user_session import UserSessionRepository, _parse_device
from backend.services.chat_agent_service import ChatAgentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users")


class UserProfileResponse(BaseModel):
    """User profile response model"""

    id: str
    auth0_id: str
    email: str
    name: str | None
    picture_url: str | None
    created_at: str
    last_login_at: str | None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """User profile update request"""

    name: str | None = Field(None, min_length=1, max_length=100)
    picture_url: str | None = None

    @field_validator("picture_url")
    @classmethod
    def validate_picture_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("picture_url must use http or https scheme")
        if not parsed.netloc:
            raise ValueError("picture_url must include a valid hostname")
        return v


@router.get("/me")
async def get_my_profile(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """
    Get current user's profile.

    Returns complete user profile information.
    """
    repo = UserRepository(db)
    user = await repo.get(auth.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserProfileResponse(
        id=str(user.id),
        auth0_id=user.auth0_id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.patch("/me")
async def update_my_profile(
    updates: UserProfileUpdate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """
    Update current user's profile.

    Users can only update their own profile.
    """
    repo = UserRepository(db)

    # Build update dict
    update_data = {}
    if updates.name is not None:
        update_data["name"] = updates.name
    if updates.picture_url is not None:
        update_data["picture_url"] = updates.picture_url

    user = await repo.update(auth.user_id, **update_data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    await db.commit()

    return UserProfileResponse(
        id=str(user.id),
        auth0_id=user.auth0_id,
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


class PublicUserProfileResponse(BaseModel):
    """Public user profile — org-scoped, no PII exposed."""

    id: str
    name: str | None
    picture_url: str | None
    created_at: str

    class Config:
        from_attributes = True


@router.get("/{user_id}")
async def get_user_profile(
    user_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PublicUserProfileResponse:
    """
    Get another user's profile (public info only).

    Restricted to users within the same organization to prevent cross-tenant
    user enumeration. Sensitive fields (email, auth0_id) are never returned.
    """
    # Prevent cross-org user enumeration: only expose users in the same org
    if user_id != auth.user_id:
        org_repo = OrganizationRepository(db, user_id=auth.user_id, request_id=None)
        membership = await org_repo.get_user_membership(auth.org_id, user_id)
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

    repo = UserRepository(db)
    user = await repo.get(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return PublicUserProfileResponse(
        id=str(user.id),
        name=user.name,
        picture_url=user.picture_url,
        created_at=user.created_at.isoformat(),
    )


# ── Privacy / Data Management ─────────────────────────────────────────────────


class ClearHistoryResponse(BaseModel):
    """Response for clearing user history"""

    deleted_sessions: int
    message: str


class DeletionRequestResponse(BaseModel):
    """Response for a GDPR data deletion request"""

    request_id: str
    status: str
    message: str


@router.delete(
    "/me/history",
    response_model=ClearHistoryResponse,
    summary="Clear all user history",
)
async def clear_my_history(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClearHistoryResponse:
    """
    Permanently delete all chat sessions and messages for the current user.

    This is a destructive, irreversible operation.
    """
    redis = await get_redis()
    service = ChatAgentService(db, redis, auth.org_id, auth.user_id)

    # Fetch all sessions (active + archived) with a high limit
    active_sessions = await service.list_sessions(status="active", skip=0, limit=1000)
    archived_sessions = await service.list_sessions(
        status="archived", skip=0, limit=1000
    )
    all_sessions = active_sessions + archived_sessions

    deleted_count = 0
    for session in all_sessions:
        success = await service.delete_session(session.id)
        if success:
            deleted_count += 1

    await db.commit()

    logger.info(
        f"Cleared history for user {auth.user_id}: deleted {deleted_count} sessions"
    )

    return ClearHistoryResponse(
        deleted_sessions=deleted_count,
        message=f"Successfully deleted {deleted_count} session(s) and all associated messages.",
    )


@router.post(
    "/me/deletion-request",
    response_model=DeletionRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request account data deletion (GDPR)",
)
async def request_data_deletion(
    request: Request,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeletionRequestResponse:
    """
    Execute a GDPR-compliant data deletion (right to be forgotten).

    Permanently deletes all user data across the platform:
    chat sessions, search history, feedback, device sessions.
    Audit logs are anonymised (PII removed, trail preserved).
    """
    repo = UserRepository(db)
    user = await repo.get(auth.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    request_id = str(_uuid.uuid4())
    requesting_ip = (request.client.host if request.client else None) or "unknown"

    try:
        counts = await delete_user_data(
            db,
            auth.user_id,
            requesting_ip=requesting_ip,
            request_id=request_id,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    logger.warning(
        f"Data deletion completed: user={auth.user_id} request_id={request_id} "
        f"counts={counts}"
    )

    # Enqueue confirmation email via RQ worker
    try:
        from backend.job_handlers import send_deletion_request_email_job
        from backend.job_queue import enqueue_job

        enqueue_job(
            send_deletion_request_email_job,
            user.email,
            request_id,
            queue_name="default",
            job_timeout="2m",
        )
        logger.info("deletion_confirmation_email_enqueued: user=%s", auth.user_id)
    except Exception:
        logger.exception("Failed to enqueue deletion confirmation email")

    return DeletionRequestResponse(
        request_id=request_id,
        status="completed",
        message=(
            "Your data has been permanently deleted. "
            f"Removed: {counts.get('chat_sessions', 0)} chat sessions, "
            f"{counts.get('search_queries', 0)} search queries, "
            f"{counts.get('user_feedback', 0)} feedback events, "
            f"{counts.get('user_sessions', 0)} device sessions. "
            f"{counts.get('audit_logs_anonymised', 0)} audit log entries anonymised."
        ),
    )


class DataExportRequestResponse(BaseModel):
    """Response for a data portability export request"""

    request_id: str
    status: str
    message: str
    data: dict | None = None


@router.post(
    "/me/data-export-request",
    response_model=DataExportRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Export all user data (GDPR portability)",
)
async def request_data_export(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataExportRequestResponse:
    """
    Return a full portable JSON export of the user's data (GDPR Article 20).

    Includes: profile, chat sessions with messages, search queries,
    feedback events, and device sessions.
    """
    repo = UserRepository(db)
    user = await repo.get(auth.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    request_id = str(_uuid.uuid4())

    try:
        export_data = await export_user_data(db, auth.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    logger.info(f"Data export completed: user={auth.user_id} request_id={request_id}")

    # Enqueue confirmation email via RQ worker
    try:
        from backend.job_handlers import send_data_export_email_job
        from backend.job_queue import enqueue_job

        enqueue_job(
            send_data_export_email_job,
            user.email,
            request_id,
            queue_name="default",
            job_timeout="2m",
        )
        logger.info("data_export_confirmation_email_enqueued: user=%s", auth.user_id)
    except Exception:
        logger.exception("Failed to enqueue data export confirmation email")

    return DataExportRequestResponse(
        request_id=request_id,
        status="completed",
        message="Your data export is ready.",
        data=export_data,
    )


# ── Session Management ────────────────────────────────────────────────────────


# ── Consent Management ─────────────────────────────────────────────────────


class ConsentRequest(BaseModel):
    """Request to record a consent decision."""

    consent_type: ConsentType
    granted: bool


class ConsentResponse(BaseModel):
    """Response after recording a consent decision."""

    user_id: str
    consent_type: str
    granted: bool
    recorded_at: str


class ConsentHistoryEntry(BaseModel):
    """A single consent change event."""

    action: str
    consent_type: str | None
    granted: bool | None
    ip_address: str | None
    recorded_at: str | None


@router.post(
    "/me/consent",
    response_model=ConsentResponse,
    summary="Record a consent decision",
)
async def update_consent(
    body: ConsentRequest,
    request: Request,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsentResponse:
    """
    Record or withdraw consent for a specific processing category.

    Categories: data_processing, marketing, analytics, ai_training.
    All consent changes are audit-logged for regulatory compliance.
    """
    ip = (request.client.host if request.client else None) or "unknown"
    ua = request.headers.get("user-agent")

    try:
        result = await record_consent(
            db,
            auth.user_id,
            body.consent_type,
            body.granted,
            ip_address=ip,
            user_agent=ua,
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return ConsentResponse(**result)


@router.get(
    "/me/consent/history",
    response_model=list[ConsentHistoryEntry],
    summary="Retrieve consent change history",
)
async def get_my_consent_history(
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConsentHistoryEntry]:
    """
    Return the full audit trail of consent changes for the current user.
    """
    entries = await get_consent_history(db, auth.user_id)
    return [ConsentHistoryEntry(**e) for e in entries]


# ── Session Management ────────────────────────────────────────────────────────


class SessionResponse(BaseModel):
    """A single device/browser session record."""

    id: str
    device: str
    ip_address: str
    last_active_at: str
    created_at: str
    is_current: bool


@router.get(
    "/me/sessions",
    response_model=list[SessionResponse],
    summary="List active sessions for the current user",
)
async def list_my_sessions(
    request: Request,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SessionResponse]:
    """
    Return all non-revoked sessions for the authenticated user.

    The session matching the current request IP + device is flagged
    as is_current=True.
    """
    repo = UserSessionRepository(db)
    sessions = await repo.list_active_sessions(auth.user_id)

    # Determine which session is the current one
    current_ip = (request.client.host if request.client else None) or "unknown"
    current_device = _parse_device(request.headers.get("user-agent"))

    return [
        SessionResponse(
            id=str(s.id),
            device=s.device,
            ip_address=s.ip_address,
            last_active_at=s.last_active_at.isoformat(),
            created_at=s.created_at.isoformat(),
            is_current=(s.ip_address == current_ip and s.device == current_device),
        )
        for s in sessions
    ]


@router.delete(
    "/me/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a specific session",
)
async def revoke_my_session(
    session_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Soft-revoke a session by ID.

    Only the owning user may revoke their own sessions.
    """
    repo = UserSessionRepository(db)
    revoked = await repo.revoke_session(session_id, auth.user_id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already revoked.",
        )


@router.delete(
    "/me/sessions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke all sessions except the current one",
)
async def revoke_all_other_sessions(
    request: Request,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Signs the user out of all devices except the one making this request.
    """
    repo = UserSessionRepository(db)
    current_ip = (request.client.host if request.client else None) or "unknown"
    current_device = _parse_device(request.headers.get("user-agent"))
    await repo.revoke_all_other_sessions(auth.user_id, current_ip, current_device)
