"""NGSI-LD client for Orion-LD."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx


# Context URIs for different entity type families
# These MUST match the @context used when creating the entities (see seed_current_data.py)
GBFS_CONTEXT = "https://raw.githubusercontent.com/smart-data-models/dataModel.GBFS/master/context.jsonld"
WEATHER_CONTEXT = "https://raw.githubusercontent.com/smart-data-models/dataModel.Weather/master/context.jsonld"
DEVICE_CONTEXT = "https://raw.githubusercontent.com/smart-data-models/dataModel.Device/master/context.jsonld"

# Map entity types to their context for Link header
TYPE_CONTEXT_MAP = {
    "station_information": GBFS_CONTEXT,
    "station_status": GBFS_CONTEXT,
    "free_bike_status": GBFS_CONTEXT,
    "system_information": GBFS_CONTEXT,
    "geofencing_zones": GBFS_CONTEXT,
    "WeatherObserved": WEATHER_CONTEXT,
    "Device": DEVICE_CONTEXT,
}


class OrionClient:
    """Minimal NGSI-LD client for the project's needs.

    Uses `application/json` + Link header for queries to ensure type matching.
    Uses `application/ld+json` for entity creation/patch (context in body).
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("ORION_URL", "http://localhost:1026")).rstrip("/")

    @staticmethod
    def _link_header(context_url: str) -> str:
        """Build a Link header value for NGSI-LD context."""
        return f'<{context_url}>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'

    @staticmethod
    def unwrap(attr: Any):
        """Return plain value for NGSI-LD attribute wrappers or the input as-is.

        Example: {'type':'Property','value': 12} -> 12
        """
        if isinstance(attr, dict) and "value" in attr:
            return attr["value"]
        return attr

    async def get_entities(self, type_: str, city: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"type": type_, "options": "keyValues"}
        if city:
            # Use id pattern matching following the URN convention
            # e.g. urn:ngsi-ld:station_information:acoruna:*
            params["idPattern"] = f"urn:ngsi-ld:{type_}:{city}:.*"

        # Use application/json + Link header so Orion can resolve short type names
        context_url = TYPE_CONTEXT_MAP.get(type_, GBFS_CONTEXT)
        headers = {
            "Accept": "application/json",
            "Link": self._link_header(context_url),
        }
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0, headers=headers) as client:
            resp = await client.get("/ngsi-ld/v1/entities", params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_entity(self, entity_id: str) -> dict[str, Any]:
        params = {"options": "keyValues"}
        # Use application/json for simpler parsing; provide a generic context
        headers = {
            "Accept": "application/json",
            "Link": self._link_header(GBFS_CONTEXT),
        }
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0, headers=headers) as client:
            resp = await client.get(f"/ngsi-ld/v1/entities/{entity_id}", params=params)
            resp.raise_for_status()
            return resp.json()

    async def patch_entity(self, entity_id: str, attrs: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/ld+json",
            "Accept": "application/ld+json",
        }
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0, headers=headers) as client:
            # NGSI-LD PATCH to /entities/{id}/attrs with JSON body
            resp = await client.patch(f"/ngsi-ld/v1/entities/{entity_id}/attrs", json=attrs)
            resp.raise_for_status()
            if resp.content:
                try:
                    return resp.json()
                except Exception:
                    return {"status": "updated"}
            return {"status": "updated"}

    async def query_entity_by_type_and_id(self, type_: str, id_hint: str) -> list[dict[str, Any]]:
        # Convenience: query entities by type and id-like hint
        results = await self.get_entities(type_, None)
        return [e for e in results if id_hint in e.get("id", "")]