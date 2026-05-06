"""Weather endpoints for the contextual assistant and dashboard feeds."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from clients.orion import OrionClient
from clients.cratedb import CrateDBClient

router = APIRouter()


@router.get("")
async def current_weather(city: str = Query(default="acoruna")) -> dict[str, Any]:
    """Return latest WeatherObserved attributes for `city`."""
    client = OrionClient()
    try:
        entities = await client.get_entities("WeatherObserved", city)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Orion-LD is not available for weather lookup.") from exc

    if not entities:
        return {"city": city, "items": []}

    ent = entities[0]
    # Extract common weather attributes (keyValues mode = already unwrapped)
    def _val(k: str):
        v = ent.get(k)
        if isinstance(v, dict):
            return v.get("value")
        return v

    return {
        "city": city,
        "windSpeed": _val("windSpeed"),
        "temperature": _val("temperature"),
        "precipitation": _val("precipitation"),
        "weatherType": _val("weatherType"),
    }


@router.get("/trips/heatmap")
async def trips_heatmap(city: str = Query(default="acoruna")) -> list[dict[str, Any]]:
    """Return aggregated trips per origin station for heatmap visualization."""
    client = CrateDBClient()
    try:
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(None, client.get_trips_heatmap)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="CrateDB is not available for analytics.") from exc

    # Rows already contain station_id, trip_count, avg_distance, intensity
    return rows