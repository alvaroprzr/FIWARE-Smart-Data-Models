"""NGSI-LD client for Orion-LD."""

from __future__ import annotations

import os
from typing import Any

import httpx


class OrionClient:
    # TODO: add the full NGSI-LD query and subscription management surface.

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("ORION_URL", "http://localhost:1026")).rstrip("/")

    async def list_entities(self, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            response = await client.get("/ngsi-ld/v1/entities", params=params or {})
            response.raise_for_status()
            return response.json()

    async def get_entity(self, entity_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            response = await client.get(f"/ngsi-ld/v1/entities/{entity_id}")
            response.raise_for_status()
            return response.json()

    async def patch_entity_attrs(self, entity_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            response = await client.patch(f"/ngsi-ld/v1/entities/{entity_id}/attrs", json=payload)
            response.raise_for_status()
            return response.json() if response.content else {"status": "updated"}