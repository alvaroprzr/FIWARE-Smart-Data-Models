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
    """Return list of stations by reading per-station `station_information` entities.

    Each station_information entity contains station metadata as direct NGSI-LD properties.
    """
    client = OrionClient()
    try:
        entities = await client.get_entities("station_information", city)
    except Exception as exc:  # pragma: no cover - scaffold fallback
        raise HTTPException(status_code=503, detail="Orion-LD is not available.") from exc

    items: list[dict[str, Any]] = []
    if entities:
        for ent in entities:
            station_id = client.unwrap(ent.get("station_id")) or client.unwrap(ent.get("https://smartdatamodels.org/dataModel.GBFS/station_id")) or ent.get("id", "").split(":")[-1]
            name = client.unwrap(ent.get("name")) or client.unwrap(ent.get("https://uri.etsi.org/ngsi-ld/name")) or f"Estación {station_id}"
            capacity = client.unwrap(ent.get("capacity")) or client.unwrap(ent.get("https://smart-data-models.github.io/data-models/terms.jsonld#/definitions/capacity")) or 20
            location = ent.get("location", {})
            loc_value = location.get("value", {}) if isinstance(location, dict) else {}
            coords = loc_value.get("coordinates", [None, None]) if isinstance(loc_value, dict) else [None, None]
            lon = coords[0] if len(coords) > 0 else None
            lat = coords[1] if len(coords) > 1 else None
            if lat is None:
                lat = client.unwrap(ent.get("lat")) or client.unwrap(ent.get("https://smartdatamodels.org/dataModel.GBFS/lat"))
            if lon is None:
                lon = client.unwrap(ent.get("lon")) or client.unwrap(ent.get("https://smartdatamodels.org/dataModel.GBFS/lon"))
            items.append({"station_id": station_id, "lat": lat, "lon": lon, "name": name, "capacity": capacity})

    return {"city": city, "items": items}


@router.get("/{station_id}/status")
async def get_station_status(station_id: str, city: str = Query(default="acoruna")) -> dict[str, Any]:
    """Return the dynamic status for a single station.

    Looks up the per-station entity: urn:ngsi-ld:station_status:{city}:{station_id}
    """
    client = OrionClient()
    entity_id = f"urn:ngsi-ld:station_status:{city}:{station_id}"

    try:
        ent = await client.get_entity(entity_id)
        # Extract expected attributes (handle both short names and expanded NGSI-LD URIs)
        attrs = {}
        for k in ("num_bikes_available", "num_docks_available", "is_renting", "last_reported"):
            raw = ent.get(k) or ent.get(f"https://smartdatamodels.org/dataModel.GBFS/{k}")
            val = client.unwrap(raw)
            attrs[k] = val
        
        # Format last_reported safely
        if isinstance(attrs.get("last_reported"), (int, float)):
            try:
                attrs["last_reported"] = datetime.fromtimestamp(int(attrs["last_reported"])).isoformat()
            except Exception:
                pass
                
        return {"station_id": station_id, **attrs}
    except Exception:
        logger.debug(f"Per-station entity {entity_id} not found")

    raise HTTPException(status_code=404, detail=f"Station {station_id} not found.")


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

    # Validate station exists (best effort) — try per-station entity first, then feed
    status_found = False
    try:
        status_id = f"urn:ngsi-ld:station_status:{city}:{station_id}"
        await orion.get_entity(status_id)
        status_found = True
    except Exception:
        pass

    if not status_found:
        # Try to find station via per-station station_information entity
        try:
            info_id = f"urn:ngsi-ld:station_information:{city}:{station_id}"
            await orion.get_entity(info_id)
            status_found = True
        except Exception:
            pass

    if not status_found:
        raise HTTPException(
            status_code=404,
            detail=f"Station {station_id} not found or Orion-LD unavailable.",
        )

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