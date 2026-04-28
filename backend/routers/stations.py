"""Station endpoints for NGSI-LD entities."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from clients.orion import OrionClient

router = APIRouter()


@router.get("")
async def list_stations(city: str = Query(default="acoruna")) -> dict[str, object]:
    # TODO: replace the placeholder fallback with the full NGSI-LD station aggregation logic.
    client = OrionClient()
    try:
        entities = await client.list_entities({"type": "station_status", "q": f"city=={city}"})
    except Exception as exc:  # pragma: no cover - scaffold fallback
        entities = []
        _ = exc
    return {"city": city, "items": entities}


@router.get("/{station_id}")
async def get_station(station_id: str) -> dict[str, object]:
    # TODO: enrich this response with station_information, status and Device relations.
    client = OrionClient()
    try:
        entity = await client.get_entity(station_id)
    except Exception as exc:  # pragma: no cover - scaffold fallback
        raise HTTPException(status_code=503, detail="Orion-LD is not available for the station lookup.") from exc
    return entity