"""Alerts and favorites endpoints.

This lightweight router stores user favorites and receives Orion notifications.
Favorites are persisted to `data/favorites.json` in a simple format.
Orion should be configured to notify POST /api/alerts/notify when station_status changes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FAV_FILE = DATA_DIR / "favorites.json"
ALERTS_LOG = DATA_DIR / "alerts.log"

router = APIRouter()

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Simple in-memory cache loaded from disk
_favorites_cache: dict[str, set[str]] = {}


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
    notified = payload.get("data") or payload.get("data") or payload
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

    return {"received": len(entries), "alerts": alerts}