"""WebSocket connection manager for Situation Room.

Manages per-industry WebSocket subscriptions, broadcasts new signals
to connected clients, and handles heartbeats. Uses Redis Pub/Sub for
cross-process signal event distribution (multiple Uvicorn workers).

Architecture:
  Client ──WS──▶ ConnectionManager ◀──Redis PubSub──▶ Signal Pipeline
                    │
                    └── per-industry rooms (dict[industry_slug, set[WebSocket]])
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from backend.observability import (
    ws_connections_active,
    ws_messages_sent_total,
    ws_rooms_active,
)
from backend.redis_client import get_redis
from backend.schemas.situation_room import (
    SituationRoomEventType,
    WSMessage,
)

logger = logging.getLogger(__name__)

# Redis Pub/Sub channel prefix
CHANNEL_PREFIX = "situation_room:"
HEARTBEAT_INTERVAL = 30  # seconds


class ConnectionManager:
    """Manages WebSocket connections grouped by industry slug.

    Thread-safe for asyncio (single event loop). For multi-worker
    deployments, Redis Pub/Sub bridges events across processes.
    """

    def __init__(self):
        # industry_slug → set of active WebSocket connections
        self._rooms: dict[str, set[WebSocket]] = {}
        # WebSocket → set of subscribed industry slugs
        self._subscriptions: dict[WebSocket, set[str]] = {}
        # Background tasks
        self._pubsub_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None

    # ── Connection Lifecycle ─────────────────────────────────────────

    async def connect(self, websocket: WebSocket, industry_slug: str) -> None:
        """Accept a WebSocket and subscribe it to an industry room."""
        await websocket.accept()

        # Add to room
        if industry_slug not in self._rooms:
            self._rooms[industry_slug] = set()
        self._rooms[industry_slug].add(websocket)

        # Track subscriptions per socket
        if websocket not in self._subscriptions:
            self._subscriptions[websocket] = set()
        self._subscriptions[websocket].add(industry_slug)

        logger.info(
            "ws_connected",
            extra={
                "industry": industry_slug,
                "room_size": len(self._rooms[industry_slug]),
            },
        )
        # Update Prometheus gauges
        ws_connections_active.set(sum(len(r) for r in self._rooms.values()))
        ws_rooms_active.set(len(self._rooms))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket from all its rooms."""
        slugs = self._subscriptions.pop(websocket, set())
        for slug in slugs:
            room = self._rooms.get(slug)
            if room:
                room.discard(websocket)
                if not room:
                    del self._rooms[slug]

        logger.info("ws_disconnected", extra={"rooms_left": list(slugs)})
        # Update Prometheus gauges
        ws_connections_active.set(sum(len(r) for r in self._rooms.values()))
        ws_rooms_active.set(len(self._rooms))

    # ── Broadcasting ─────────────────────────────────────────────────

    async def broadcast_to_room(
        self,
        industry_slug: str,
        message: WSMessage,
    ) -> None:
        """Send a message to all clients subscribed to an industry room."""
        room = self._rooms.get(industry_slug)
        if not room:
            return

        payload = message.model_dump_json()
        disconnected: list[WebSocket] = []
        sent_count = 0

        for ws in room:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(payload)
                    sent_count += 1
                else:
                    disconnected.append(ws)
            except Exception:
                disconnected.append(ws)

        ws_messages_sent_total.inc(sent_count)

        # Clean up dead connections
        for ws in disconnected:
            await self.disconnect(ws)

    async def broadcast_event(
        self,
        industry_slug: str,
        event_type: SituationRoomEventType,
        data: dict[str, Any],
    ) -> None:
        """Convenience: wrap data in WSMessage and broadcast."""
        msg = WSMessage(
            event=event_type,
            data=data,
            timestamp=datetime.now(timezone.utc),
            industry_id=None,  # Set by caller if needed
        )
        await self.broadcast_to_room(industry_slug, msg)

    # ── Redis Pub/Sub (Cross-Process) ────────────────────────────────

    async def publish_signal_event(
        self,
        industry_slug: str,
        event_type: SituationRoomEventType,
        data: dict[str, Any],
    ) -> None:
        """Publish a signal event to Redis for all workers to broadcast.

        Call this from the signal acquisition pipeline when a new signal
        is ingested, scored, or when an anomaly is detected.
        """
        try:
            redis = await get_redis()
            channel = f"{CHANNEL_PREFIX}{industry_slug}"
            payload = json.dumps(
                {
                    "event": event_type.value,
                    "data": _serialize_data(data),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "industry_slug": industry_slug,
                }
            )
            await redis.publish(channel, payload)
        except Exception as e:
            logger.error("redis_publish_failed", extra={"error": str(e)})

    async def start_pubsub_listener(self) -> None:
        """Start background task that subscribes to Redis Pub/Sub
        and forwards events to local WebSocket rooms.

        Call once during app startup.
        """
        if self._pubsub_task and not self._pubsub_task.done():
            return

        self._pubsub_task = asyncio.create_task(self._listen_redis_pubsub())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("pubsub_listener_started")

    async def stop_pubsub_listener(self) -> None:
        """Stop background Pub/Sub listener. Call on app shutdown."""
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        logger.info("pubsub_listener_stopped")

    async def _listen_redis_pubsub(self) -> None:
        """Background loop: subscribe to situation_room:* channels."""
        try:
            redis = await get_redis()
            pubsub = redis.pubsub()
            await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")

            async for message in pubsub.listen():
                if message["type"] != "pmessage":
                    continue

                try:
                    payload = json.loads(message["data"])
                    industry_slug = payload.get("industry_slug", "")
                    event_type = SituationRoomEventType(payload["event"])

                    await self.broadcast_event(
                        industry_slug,
                        event_type,
                        payload.get("data", {}),
                    )
                except Exception as e:
                    logger.warning(
                        "pubsub_message_error",
                        extra={"error": str(e)},
                    )

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("pubsub_listener_error", extra={"error": str(e)})
            # Retry after delay
            await asyncio.sleep(5)
            self._pubsub_task = asyncio.create_task(self._listen_redis_pubsub())

    # ── Heartbeat ────────────────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to all connected clients."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                for slug in list(self._rooms.keys()):
                    await self.broadcast_event(
                        slug,
                        SituationRoomEventType.HEARTBEAT,
                        {"connected_clients": len(self._rooms.get(slug, set()))},
                    )
        except asyncio.CancelledError:
            raise

    # ── Stats ────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Return connection statistics."""
        return {
            "total_connections": sum(len(r) for r in self._rooms.values()),
            "rooms": {slug: len(clients) for slug, clients in self._rooms.items()},
            "active_rooms": len(self._rooms),
        }


# ── Module Singleton ─────────────────────────────────────────────────

_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """Get or create the global ConnectionManager singleton."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


# ── Helpers ──────────────────────────────────────────────────────────


def _serialize_data(data: dict[str, Any]) -> dict[str, Any]:
    """Make data JSON-serializable (convert UUIDs, datetimes)."""
    result = {}
    for k, v in data.items():
        if isinstance(v, UUID):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = _serialize_data(v)
        elif isinstance(v, list):
            result[k] = [
                (
                    _serialize_data(i)
                    if isinstance(i, dict)
                    else str(i)
                    if isinstance(i, (UUID, datetime))
                    else i
                )
                for i in v
            ]
        else:
            result[k] = v
    return result
