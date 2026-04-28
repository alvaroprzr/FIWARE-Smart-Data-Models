"""Weather endpoints for the contextual assistant and dashboard feeds."""

from __future__ import annotations

from fastapi import APIRouter, Query

from clients.orion import OrionClient

router = APIRouter()


@router.get("/current")
async def current_weather(city: str = Query(default="acoruna")) -> dict[str, object]:
    # TODO: expose the WeatherObserved entity and the latest weather-derived analytics.
    client = OrionClient()
    try:
        entities = await client.list_entities({"type": "WeatherObserved", "q": f"city=={city}"})
    except Exception:
        entities = []
    return {"city": city, "items": entities}