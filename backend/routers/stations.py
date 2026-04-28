"""Station endpoints for NGSI-LD entities."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from clients.orion import OrionClient
from ml.predictor import PredictionInput, predict_availability

router = APIRouter()


@router.get("")
async def list_stations(city: str = Query(default="acoruna")) -> dict[str, Any]:
    """Return list of stations by reading the single `station_information` feed.

    The `station_information` entity contains `data.stations[]` with the static catalog.
    """
    client = OrionClient()
    try:
        entities = await client.get_entities("station_information", city)
    except Exception as exc:  # pragma: no cover - scaffold fallback
        raise HTTPException(status_code=503, detail="Orion-LD is not available.") from exc

    items: list[dict[str, Any]] = []
    if entities:
        ent = entities[0]
        data = ent.get("data") or ent.get("data", {})
        stations = data.get("stations") or ent.get("stations") or []
        for s in stations:
            # Map common fields with fallbacks
            station_id = s.get("station_id") or s.get("stationId") or s.get("id")
            lat = s.get("lat") or (s.get("location", {}).get("latitude") if isinstance(s.get("location"), dict) else None)
            lon = s.get("lon") or (s.get("location", {}).get("longitude") if isinstance(s.get("location"), dict) else None)
            name = s.get("name") or s.get("station_name")
            capacity = s.get("capacity") or s.get("slots")
            items.append({"station_id": station_id, "lat": lat, "lon": lon, "name": name, "capacity": capacity})

    return {"city": city, "items": items}


@router.get("/{station_id}/status")
async def get_station_status(station_id: str) -> dict[str, Any]:
    """Return the dynamic status for a single station (NGSI-LD `station_status` entity)."""
    client = OrionClient()
    entity_id = f"urn:ngsi-ld:station_status:acoruna:{station_id}"
    try:
        ent = await client.get_entity(entity_id)
    except Exception as exc:  # pragma: no cover - scaffold fallback
        raise HTTPException(status_code=503, detail="Orion-LD is not available for the station lookup.") from exc

    # Extract expected attributes
    attrs = {}
    for k in ("num_bikes_available", "num_docks_available", "is_renting", "last_reported"):
        val = ent.get(k)
        if val is None:
            # NGSI-LD attribute might be object with 'value'
            maybe = ent.get(k) or (ent.get(k, {}).get("value") if isinstance(ent.get(k), dict) else None)
            val = maybe
        attrs[k] = val

    return {"station_id": station_id, **attrs}


@router.get("/{station_id}/prediction")
async def station_prediction(station_id: str) -> dict[str, Any]:
    """Return short-term predictions (t30, t60) for a station.

    Gathers current status and contextual weather, then calls the predictor.
    """
    orion = OrionClient()
    status_id = f"urn:ngsi-ld:station_status:acoruna:{station_id}"
    try:
        status = await orion.get_entity(status_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Orion-LD is not available for prediction lookup.") from exc

    # Best-effort extraction of current bikes
    current_bikes = None
    if isinstance(status.get("num_bikes_available"), dict):
        current_bikes = status.get("num_bikes_available", {}).get("value")
    else:
        current_bikes = status.get("num_bikes_available")

    # Get weather (latest)
    try:
        weather_entities = await orion.get_entities("WeatherObserved", "acoruna")
        weather = weather_entities[0] if weather_entities else {}
        wind = weather.get("windSpeed") or (weather.get("windSpeed", {}).get("value") if isinstance(weather.get("windSpeed"), dict) else None)
    except Exception:
        wind = None

    # Build predictor input
    inp = PredictionInput(station_id=station_id, horizon_minutes=30, num_bikes_available=int(current_bikes or 0))
    p30 = predict_availability(inp)
    inp60 = PredictionInput(station_id=station_id, horizon_minutes=60, num_bikes_available=int(current_bikes or 0))
    p60 = predict_availability(inp60)

    return {"station_id": station_id, "t30": p30.predicted_num_bikes_available, "t60": p60.predicted_num_bikes_available, "windSpeed": wind}