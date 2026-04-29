"""NGSI-LD client for Orion-LD."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx


class OrionClient:
    """Minimal NGSI-LD client for the project's needs.

    Uses `application/ld+json` headers for NGSI-LD requests.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("ORION_URL", "http://localhost:1026")).rstrip("/")
        self._headers = {
            "Content-Type": "application/ld+json",
            "Accept": "application/ld+json",
        }

    async def get_entities(self, type_: str, city: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"type": type_}
        if city:
            # Try to match either nested station address or top-level addressLocality
            q = f"data.stations[].address.addressLocality==\"{city}\" OR address.addressLocality==\"{city}\""
            params["q"] = q
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0, headers=self._headers) as client:
            resp = await client.get("/ngsi-ld/v1/entities", params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_entity(self, entity_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0, headers=self._headers) as client:
            resp = await client.get(f"/ngsi-ld/v1/entities/{entity_id}")
            resp.raise_for_status()
            return resp.json()

    async def patch_entity(self, entity_id: str, attrs: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0, headers=self._headers) as client:
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