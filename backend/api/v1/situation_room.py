"""Situation Room API endpoints.

REST snapshot plus WebSocket real-time feed for live industry dashboards.
"""

import json
import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.schemas import AuthContext
from backend.database import get_db, get_db_read
from backend.middleware.feature_gating import require_feature
from backend.schemas.situation_room import (
    SituationRoomDashboard,
    SituationRoomEventType,
    WSMessage,
)
from backend.services.gating_service import GatingService
from backend.services.situation_room import SituationRoomService
from backend.services.ws_manager import get_connection_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/situation-room")
WS_TICKET_TTL_SECONDS = 60

_ALLOWED_SIGNAL_TYPES = frozenset(
    {"news", "social", "regulatory", "financial", "market", "technology"}
)


class WebSocketTicketResponse(BaseModel):
    ticket: str
    expires_in: int


def _ws_ticket_key(ticket: str) -> str:
    return f"ws-ticket:situation-room:{ticket}"


async def _issue_ws_ticket(auth: AuthContext, industry_slug: str) -> str:
    from backend.redis_client import get_redis

    ticket = secrets.token_urlsafe(32)
    redis = await get_redis()
    await redis.set(
        _ws_ticket_key(ticket),
        json.dumps(
            {
                "user_id": str(auth.user_id),
                "auth0_id": auth.auth0_id,
                "email": auth.email,
                "org_id": str(auth.org_id),
                "role": auth.role,
                "plan": auth.plan,
                "is_super_admin": auth.is_super_admin,
                "token_expires_at": auth.token_expires_at.isoformat(),
                "request_id": auth.request_id,
                "industry_slug": industry_slug,
            }
        ),
        ex=WS_TICKET_TTL_SECONDS,
    )
    return ticket


async def _consume_ws_ticket(ticket: str, industry_slug: str) -> AuthContext | None:
    from backend.redis_client import get_redis

    redis = await get_redis()
    key = _ws_ticket_key(ticket)
    raw = await redis.get(key)
    if raw is None:
        return None
    await redis.delete(key)

    payload = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    if payload.get("industry_slug") != industry_slug:
        return None

    return AuthContext(
        user_id=UUID(payload["user_id"]),
        auth0_id=payload["auth0_id"],
        email=payload["email"],
        org_id=UUID(payload["org_id"]),
        role=payload["role"],
        plan=payload["plan"],
        is_super_admin=payload["is_super_admin"],
        token_expires_at=datetime.fromisoformat(payload["token_expires_at"]),
        request_id=payload.get("request_id"),
    )


async def _auth_from_legacy_query_token(
    websocket: WebSocket,
    db: AsyncSession,
) -> AuthContext | None:
    token = websocket.query_params.get("token")
    if not token:
        return None

    from backend.auth import utils as auth_utils
    from backend.auth.dependencies import _handle_m2m_token, _handle_user_token

    payload = await auth_utils.verify_token(token)
    auth_utils.validate_custom_claims(payload)
    if payload.is_m2m_token:
        return await _handle_m2m_token(payload, websocket, db)  # type: ignore[arg-type]
    return await _handle_user_token(payload, websocket, db)  # type: ignore[arg-type]


@router.get("/stats", response_model=dict)
async def get_ws_stats(
    auth: AuthContext = Depends(get_current_user),
):
    """Get WebSocket connection statistics. Admin only."""
    if not auth.is_admin_or_higher:
        raise HTTPException(status_code=403, detail="Admin access required")

    manager = get_connection_manager()
    return manager.get_stats()


@router.post("/{industry_slug}/ws-ticket", response_model=WebSocketTicketResponse)
async def create_situation_room_ws_ticket(
    industry_slug: str,
    auth: AuthContext = Depends(get_current_user),
    _feature_check: bool = Depends(require_feature("situation_room")),
):
    """Issue a short-lived, single-use ticket for the WebSocket handshake."""
    ticket = await _issue_ws_ticket(auth, industry_slug)
    return WebSocketTicketResponse(ticket=ticket, expires_in=WS_TICKET_TTL_SECONDS)


@router.get("/{industry_slug}", response_model=SituationRoomDashboard)
async def get_situation_room_dashboard(
    industry_slug: str,
    signal_types: str | None = Query(
        None,
        description="Comma-separated signal types: news,social,regulatory,financial,market,technology",
    ),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    hours: int = Query(
        168, ge=1, le=720, description="Lookback window (default 7d, max 30d)"
    ),
    limit: int = Query(50, ge=1, le=200, description="Max signals in feed"),
    db: AsyncSession = Depends(get_db_read),
    auth: AuthContext = Depends(get_current_user),
    _feature_check: bool = Depends(require_feature("situation_room")),
):
    """Get a full dashboard snapshot for an industry."""
    types_list = None
    if signal_types:
        types_list = [t.strip() for t in signal_types.split(",") if t.strip()]
        invalid = [t for t in types_list if t not in _ALLOWED_SIGNAL_TYPES]
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid signal_types: {invalid}. "
                    f"Allowed: {sorted(_ALLOWED_SIGNAL_TYPES)}"
                ),
            )

    service = SituationRoomService(db)
    try:
        return await service.get_dashboard(
            industry_slug,
            org_id=auth.org_id,
            signal_types=types_list,
            min_confidence=min_confidence,
            hours=hours,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.websocket("/{industry_slug}/live")
async def situation_room_websocket(
    websocket: WebSocket,
    industry_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint for real-time signal updates."""
    manager = get_connection_manager()

    auth_context: AuthContext | None = None
    ticket = websocket.query_params.get("ticket")
    if ticket:
        try:
            auth_context = await _consume_ws_ticket(ticket, industry_slug)
        except Exception as e:
            logger.warning("ws_ticket_failed", extra={"error": str(e)})

    if auth_context is None:
        try:
            auth_context = await _auth_from_legacy_query_token(websocket, db)
            if auth_context:
                logger.warning(
                    "ws_legacy_query_token_used",
                    extra={"industry": industry_slug},
                )
        except Exception as e:
            logger.warning("ws_auth_failed", extra={"error": str(e)})
            await websocket.close(code=4003, reason="Invalid authentication token")
            return

    if auth_context is None:
        await websocket.close(code=4001, reason="Missing authentication ticket")
        return

    from backend.repositories.organization import OrganizationRepository

    org_repo = OrganizationRepository(db)
    org = await org_repo.get(auth_context.org_id)
    if not org:
        await websocket.close(code=4003, reason="Organization not found")
        return

    gating = GatingService(db)
    gate = await gating.feature_gate_repo.get_by_feature_key("situation_room")
    if gate and not gating._check_tier_access(org.pricing_tier, gate.required_tier):
        logger.warning(
            "ws_tier_gate_denied",
            extra={"org": str(auth_context.org_id), "tier": org.pricing_tier},
        )
        await websocket.close(
            code=4003,
            reason=f"Situation Room requires {gate.required_tier} tier or higher",
        )
        return

    logger.info(
        "ws_authenticated",
        extra={
            "user": str(auth_context.user_id),
            "org": str(auth_context.org_id),
            "industry": industry_slug,
        },
    )

    await manager.connect(websocket, industry_slug)

    try:
        service = SituationRoomService(db)
        try:
            dashboard = await service.get_dashboard(
                industry_slug,
                org_id=auth_context.org_id,
                hours=24,
                limit=20,
            )
            initial_msg = WSMessage(
                event=SituationRoomEventType.INITIAL_STATE,
                data=dashboard.model_dump(mode="json"),
                timestamp=datetime.now(timezone.utc),
                industry_id=dashboard.industry_id,
            )
            await websocket.send_text(initial_msg.model_dump_json())
        except ValueError:
            error_msg = WSMessage(
                event=SituationRoomEventType.ERROR,
                data={"message": f"Industry not found: {industry_slug}"},
                timestamp=datetime.now(timezone.utc),
            )
            await websocket.send_text(error_msg.model_dump_json())
            await manager.disconnect(websocket)
            await websocket.close(code=4004, reason="Industry not found")
            return

        while True:
            try:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                    if msg.get("action") == "ping":
                        pong = WSMessage(
                            event=SituationRoomEventType.HEARTBEAT,
                            data={"pong": True},
                            timestamp=datetime.now(timezone.utc),
                        )
                        await websocket.send_text(pong.model_dump_json())
                except json.JSONDecodeError:
                    pass
            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error("ws_error", extra={"error": str(e)})
    finally:
        await manager.disconnect(websocket)
