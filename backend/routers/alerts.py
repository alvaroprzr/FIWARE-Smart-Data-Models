"""Alerts and favorites endpoints.

This lightweight router stores user favorites and receives Orion notifications.
Favorites are persisted to `data/favorites.json` in a simple format.
Orion should be configured to notify POST /api/alerts/notify when station_status changes.
Alert delivery uses Server-Sent Events (SSE): clients connect to GET /api/alerts/stream
and receive real-time push events when a favorited station becomes available (0 → ≥1 bikes).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FAV_FILE = DATA_DIR / "favorites.json"
ALERTS_LOG = DATA_DIR / "alerts.log"

router = APIRouter()

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Simple in-memory cache loaded from disk
_favorites_cache: dict[str, set[str]] = {}

# SSE subscriber queues: client_id -> asyncio.Queue of event dicts
_sse_subscribers: dict[str, list[asyncio.Queue]] = {}

# Track last known bike count per station to detect 0 -> ≥1 transitions
_last_bike_count: dict[str, int] = {}


def _load_favorites() -> None:
    global _favorites_cache
    if FAV_FILE.exists():
        try:
            with open(FAV_FILE, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
                _favorites_cache = {k: set(v) for k, v in raw.items()}
        except Exception:
            _favorites_cache = {}
    else:
        _favorites_cache = {}


def _save_favorites() -> None:
    try:
        with open(FAV_FILE, "w", encoding="utf-8") as fh:
            json.dump({k: list(v) for k, v in _favorites_cache.items()}, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


class FavoriteRequest(BaseModel):
    client_id: str = Field(min_length=1)
    station_id: str = Field(min_length=1)


class FavoriteDeleteRequest(BaseModel):
    client_id: str = Field(min_length=1)
    station_id: str = Field(min_length=1)


@router.on_event("startup")
async def _init_favs():
    _load_favorites()


@router.post("/favorite")
async def add_favorite(req: FavoriteRequest) -> dict[str, Any]:
    """Add a favorite station for a client (idempotent)."""
    client = req.client_id
    sid = req.station_id
    if client not in _favorites_cache:
        _favorites_cache[client] = set()
    _favorites_cache[client].add(sid)
    _save_favorites()
    return {"status": "ok", "client_id": client, "station_id": sid}


@router.get("/favorites")
async def get_favorites(client_id: str) -> dict[str, Any]:
    items = list(_favorites_cache.get(client_id, []))
    return {"client_id": client_id, "favorites": items}


@router.delete("/favorite")
async def remove_favorite(req: FavoriteDeleteRequest) -> dict[str, Any]:
    """Remove a favorite station for a client (idempotent)."""
    client = req.client_id
    sid = req.station_id
    if client in _favorites_cache and sid in _favorites_cache[client]:
        _favorites_cache[client].remove(sid)
        if not _favorites_cache[client]:
            _favorites_cache.pop(client, None)
        _save_favorites()
    return {"status": "ok", "client_id": client, "station_id": sid}


@router.get("/stream")
async def alert_stream(client_id: str, request: Request) -> StreamingResponse:
    """Server-Sent Events endpoint for real-time alert delivery.

    Clients connect here and receive push notifications when a favorited station
    transitions from 0 to ≥1 available bikes.
    """
    queue: asyncio.Queue = asyncio.Queue()
    if client_id not in _sse_subscribers:
        _sse_subscribers[client_id] = []
    _sse_subscribers[client_id].append(queue)

    async def event_generator():
        try:
            yield "data: {\"type\": \"connected\"}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            if client_id in _sse_subscribers and queue in _sse_subscribers[client_id]:
                _sse_subscribers[client_id].remove(queue)
                if not _sse_subscribers[client_id]:
                    _sse_subscribers.pop(client_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/notify")
async def orion_notify(request: Request) -> dict[str, Any]:
    """Endpoint to receive Orion notifications (to be used by subscriptions).

    This function parses the incoming notification payload (NGSI-LD notify format)
    and if any favorite clients are affected, an alert line is appended to alerts.log.
    Actual push delivery is out of scope for the MVP; alerts are persisted to disk.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Orion notify structure varies; try to extract entity id and changed attributes
    notified = payload.get("data") or payload
    # payload may be a dict with 'data': [ {entity} ]
    entries = []
    if isinstance(notified, dict) and "data" in notified and isinstance(notified["data"], list):
        entries = notified["data"]
    elif isinstance(payload, list):
        entries = payload
    elif isinstance(payload, dict) and "id" in payload:
        entries = [payload]

    alerts = []
    for ent in entries:
        entity_id = ent.get("id") or ent.get("entityId") or ""
        # try to extract station id from entity or attributes
        station_id = None
        sid = ent.get("station_id") or ent.get("stationId") or None
        if isinstance(sid, dict):
            station_id = sid.get("value")
        elif isinstance(sid, str):
            station_id = sid
        if not station_id:
            # try to parse urn parts
            if entity_id and ":" in entity_id:
                parts = entity_id.split(":")
                station_id = parts[-1]
        if not station_id:
            continue

        # Extract current bike count to detect 0 -> ≥1 transition
        num_bikes = None
        raw_bikes = ent.get("num_bikes_available")
        if isinstance(raw_bikes, dict):
            num_bikes = raw_bikes.get("value")
        elif isinstance(raw_bikes, (int, float)):
            num_bikes = raw_bikes
        try:
            num_bikes = int(num_bikes) if num_bikes is not None else None
        except (TypeError, ValueError):
            num_bikes = None

        prev_count = _last_bike_count.get(station_id)
        if num_bikes is not None:
            _last_bike_count[station_id] = num_bikes

        availability_restored = (
            num_bikes is not None
            and num_bikes >= 1
            and prev_count is not None
            and prev_count == 0
        )

        # Find clients who favorited this station
        targets = [c for c, sset in _favorites_cache.items() if station_id in sset]
        if targets:
            line = {"station_id": station_id, "entity_id": entity_id, "targets": targets}
            # append to alerts log
            try:
                with open(ALERTS_LOG, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(line, ensure_ascii=False) + "\n")
            except Exception:
                pass
            alerts.append(line)

            # Push SSE event to connected clients when availability is restored
            if availability_restored:
                event = {
                    "type": "availability_restored",
                    "station_id": station_id,
                    "num_bikes_available": num_bikes,
                }
                for client_id in targets:
                    for q in list(_sse_subscribers.get(client_id, [])):
                        try:
                            q.put_nowait(event)
                        except asyncio.QueueFull:
                            pass

    return {"received": len(entries), "alerts": alerts}