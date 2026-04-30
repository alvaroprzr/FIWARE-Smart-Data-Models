"""Station endpoints for NGSI-LD entities."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from clients.orion import OrionClient
from ml.predictor import predict

logger = logging.getLogger(__name__)

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
async def get_station_status(station_id: str, city: str = Query(default="acoruna")) -> dict[str, Any]:
    """Return the dynamic status for a single station (NGSI-LD `station_status` entity)."""
    client = OrionClient()
    entity_id = f"urn:ngsi-ld:station_status:{city}:{station_id}"
    try:
        ent = await client.get_entity(entity_id)
    except Exception as exc:  # pragma: no cover - scaffold fallback
        raise HTTPException(status_code=503, detail="Orion-LD is not available for the station lookup.") from exc

    # Extract expected attributes (use unwrap helper as fallback)
    attrs = {}
    for k in ("num_bikes_available", "num_docks_available", "is_renting", "last_reported"):
        raw = ent.get(k)
        val = client.unwrap(raw)
        attrs[k] = val

    return {"station_id": station_id, **attrs}


@router.get("/{station_id}/forecast")
async def get_station_forecast(station_id: str, city: str = Query(default="acoruna")) -> dict[str, Any]:
    """Return demand forecast (t+30min, t+60min) for a station.

    Gathers current conditions (time, weather) and calls the predictor model.
    Uses pre-trained RandomForest models if available; falls back to
    per-station/per-hour historical means otherwise.

    Returns:
        {
            "station_id": str,
            "t30": {"value": float, "low": float, "high": float},
            "t60": {"value": float, "low": float, "high": float},
            "model_used": "random_forest" | "fallback",
            "forecast_time": ISO datetime
        }
    """
    orion = OrionClient()

    # Validate station exists (best effort)
    status_id = f"urn:ngsi-ld:station_status:{city}:{station_id}"
    try:
        status = await orion.get_entity(status_id)
    except Exception as exc:
        logger.warning(f"Station {station_id} lookup failed: {exc}")
        raise HTTPException(
            status_code=404,
            detail=f"Station {station_id} not found or Orion-LD unavailable.",
        ) from exc

    # Get current weather
    try:
        weather_entities = await orion.get_entities("WeatherObserved", city)
        weather = weather_entities[0] if weather_entities else {}
    except Exception:
        weather = {}
        logger.warning("Could not fetch weather data from Orion-LD")

    # Extract weather attributes (handle NGSI-LD value wrappers)
    def extract_value(entity: dict, key: str, default: float = 0.0) -> float:
        """Extract numeric value from NGSI-LD entity (handles both raw and wrapped formats)."""
        raw = entity.get(key)
        if raw is None:
            return default
        val = orion.unwrap(raw)
        try:
            return float(val)
        except Exception:
            return default

    wind_speed = extract_value(weather, "windSpeed", 0.0)
    precipitation = extract_value(weather, "precipitation", 0.0)

    # Get current time features
    now = datetime.now()
    hour = now.hour
    weekday = now.weekday()

    # Call predictor with current features
    try:
        forecast = predict(
            station_id=station_id,
            hour=hour,
            weekday=weekday,
            wind_speed=wind_speed,
            precipitation=precipitation,
        )
        forecast["station_id"] = station_id
        forecast["forecast_time"] = now.isoformat()
        return forecast
    except Exception as e:
        logger.error(f"Prediction failed for {station_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Forecast generation failed.",
        ) from e