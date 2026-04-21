"""Situation Room API endpoints.

REST snapshot + WebSocket real-time feed for live industry dashboards.

Endpoints:
  GET  /api/v1/situation-room/stats           → WebSocket connection stats
  GET  /api/v1/situation-room/{industry}       → Dashboard snapshot
  WS   /api/v1/situation-room/{industry}/live  → Real-time signal push
"""

import logging
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
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

_ALLOWED_SIGNAL_TYPES = frozenset(
    {"news", "social", "regulatory", "financial", "market", "technology"}
)


# ── REST: Connection Stats (must be before /{industry_slug}) ─────────


@router.get("/stats", response_model=dict)
async def get_ws_stats(
    auth: AuthContext = Depends(get_current_user),
):
    """Get WebSocket connection statistics (admin only)."""
    if not auth.is_admin_or_higher:
        raise HTTPException(status_code=403, detail="Admin access required")

    manager = get_connection_manager()
    return manager.get_stats()


# ── REST: Dashboard Snapshot ─────────────────────────────────────────


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
    """Get a full dashboard snapshot for an industry.

    Returns aggregate metrics, recent signal feed, active alerts,
    and published briefs for the Situation Room view.
    """
    types_list = None
    if signal_types:
        types_list = [t.strip() for t in signal_types.split(",") if t.strip()]
        invalid = [t for t in types_list if t not in _ALLOWED_SIGNAL_TYPES]
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid signal_types: {invalid}. Allowed: {sorted(_ALLOWED_SIGNAL_TYPES)}",
            )

    service = SituationRoomService(db)
    try:
        dashboard = await service.get_dashboard(
            industry_slug,
            org_id=auth.org_id,
            signal_types=types_list,
            min_confidence=min_confidence,
            hours=hours,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return dashboard


# ── WebSocket: Real-Time Feed ────────────────────────────────────────


@router.websocket("/{industry_slug}/live")
async def situation_room_websocket(
    websocket: WebSocket,
    industry_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint for real-time signal updates.

    Protocol:
      1. Client connects to /api/v1/situation-room/{industry}/live
      2. Server accepts and sends initial_state with recent signals
      3. Server pushes new_signal, anomaly_detected, etc. as they occur
      4. Server sends heartbeat every 30s
      5. Client can send JSON: {"action": "ping"} to keep alive

    Authentication:
      Token passed as query param: ?token=<jwt>
      Validated on connect; connection rejected if invalid.
    """
    manager = get_connection_manager()

    # Authenticate via query parameter (WebSocket can't use headers easily)
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    # Validate token
    try:
        from backend.auth.utils import verify_token

        token_payload = await verify_token(token)
        # Token is valid — user is authenticated
        logger.info(
            "ws_authenticated",
            extra={"user": token_payload.sub, "industry": industry_slug},
        )
    except Exception as e:
        logger.warning("ws_auth_failed", extra={"error": str(e)})
        await websocket.close(code=4003, reason="Invalid authentication token")
        return

    # Tier gate check — situation_room requires growth+
    if token_payload.org_id:
        from backend.repositories.organization import OrganizationRepository

        org_repo = OrganizationRepository(db)
        org = await org_repo.get(token_payload.org_id)
        if org:
            gating = GatingService(db)
            gate = await gating.feature_gate_repo.get_by_feature_key("situation_room")
            if gate and not gating._check_tier_access(
                org.pricing_tier, gate.required_tier
            ):
                logger.warning(
                    "ws_tier_gate_denied",
                    extra={"org": str(token_payload.org_id), "tier": org.pricing_tier},
                )
                await websocket.close(
                    code=4003,
                    reason=f"Situation Room requires {gate.required_tier} tier or higher",
                )
                return

    # Connect and subscribe to industry room
    await manager.connect(websocket, industry_slug)

    try:
        # Send initial state with recent signals
        service = SituationRoomService(db)
        try:
            dashboard = await service.get_dashboard(
                industry_slug,
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

        # Listen for client messages (keepalive / unsubscribe)
        while True:
            try:
                raw = await websocket.receive_text()
                # Client can send ping to keep alive
                import json

                try:
                    msg = json.loads(raw)
                    action = msg.get("action", "")

                    if action == "ping":
                        pong = WSMessage(
                            event=SituationRoomEventType.HEARTBEAT,
                            data={"pong": True},
                            timestamp=datetime.now(timezone.utc),
                        )
                        await websocket.send_text(pong.model_dump_json())

                except json.JSONDecodeError:
                    pass  # Ignore malformed messages

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error("ws_error", extra={"error": str(e)})
    finally:
        await manager.disconnect(websocket)
