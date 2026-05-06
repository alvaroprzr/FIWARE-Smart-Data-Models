"""NGSI-LD client for Orion-LD."""

from __future__ import annotations

import json
import os
import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)


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
        self.fiware_service = os.getenv("FIWARE_SERVICE", "smartmobilityhub")
        self.fiware_servicepath = os.getenv("FIWARE_SERVICEPATH", "/acoruna")
        self.timeout = httpx.Timeout(10.0, connect=5.0)

    @staticmethod
    def _link_header(context_url: str) -> str:
        """Build a Link header value for NGSI-LD context."""
        return f'<{context_url}>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'

    def _headers(self, context_url: str | None = None) -> dict[str, str]:
        headers = {
            "Fiware-Service": self.fiware_service,
            "Fiware-ServicePath": self.fiware_servicepath,
            "Accept": "application/ld+json",
        }
        if context_url:
            headers["Link"] = self._link_header(context_url)
        return headers

    @staticmethod
    def unwrap(attr: Any):
        """Return plain value for NGSI-LD attribute wrappers or the input as-is.

        Example: {'type':'Property','value': 12} -> 12
        """
        if isinstance(attr, dict) and "value" in attr:
            return attr["value"]
        return attr

    async def get_entities(
        self,
        type_: str,
        city: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"type": type_, "limit": limit, "offset": offset, "count": "true"}
        if city:
            # Use id pattern matching following the URN convention
            # e.g. urn:ngsi-ld:station_information:acoruna:*
            params["idPattern"] = f"urn:ngsi-ld:{type_}:{city}:.*"

        # Use application/ld+json + Link header so Orion can resolve short type names
        context_url = TYPE_CONTEXT_MAP.get(type_, GBFS_CONTEXT)
        headers = self._headers(context_url)
        results: list[dict[str, Any]] = []
        current_offset = offset
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, headers=headers) as client:
            while True:
                params["offset"] = current_offset
                try:
                    resp = await client.get("/ngsi-ld/v1/entities", params=params)
                    resp.raise_for_status()
                    page = resp.json()
                    if not isinstance(page, list):
                        logger.warning("Unexpected Orion response for type %s", type_)
                        return results
                    results.extend(page)
                    if len(page) < limit:
                        break
                    current_offset += limit
                except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as exc:
                    logger.exception("Orion get_entities failed for type=%s city=%s", type_, city)
                    raise RuntimeError(f"Orion query failed for {type_}") from exc
        return results

    async def get_entity(self, entity_id: str) -> dict[str, Any]:
        headers = self._headers(GBFS_CONTEXT)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, headers=headers) as client:
            try:
                resp = await client.get(f"/ngsi-ld/v1/entities/{entity_id}")
                resp.raise_for_status()
                payload = resp.json()
                if isinstance(payload, dict):
                    return payload
                logger.warning("Unexpected Orion entity payload for %s", entity_id)
                return {}
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as exc:
                logger.exception("Orion get_entity failed for %s", entity_id)
                raise RuntimeError(f"Orion query failed for {entity_id}") from exc

    async def patch_entity(self, entity_id: str, attrs: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Accept": "application/ld+json",
            "Content-Type": "application/ld+json",
            "Fiware-Service": self.fiware_service,
            "Fiware-ServicePath": self.fiware_servicepath,
        }
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, headers=headers) as client:
            # NGSI-LD PATCH to /entities/{id}/attrs with JSON body
            try:
                resp = await client.patch(f"/ngsi-ld/v1/entities/{entity_id}/attrs", json=attrs)
                resp.raise_for_status()
                if resp.content:
                    try:
                        payload = resp.json()
                        if isinstance(payload, dict):
                            return payload
                    except Exception:
                        pass
                return {"status": "updated"}
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as exc:
                logger.exception("Orion patch_entity failed for %s", entity_id)
                raise RuntimeError(f"Orion update failed for {entity_id}") from exc

    async def query_entity_by_type_and_id(self, type_: str, id_hint: str) -> list[dict[str, Any]]:
        # Convenience: query entities by type and id-like hint
        results = await self.get_entities(type_, None)
        return [e for e in results if id_hint in e.get("id", "")]