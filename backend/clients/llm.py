"""LM Studio client using the OpenAI-compatible API."""

from __future__ import annotations

import os
from typing import Any

import httpx


class LMStudioClient:
    # TODO: add prompt templates and tool-calling orchestration helpers.

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1")).rstrip("/")
        self.model = model or os.getenv("LM_STUDIO_MODEL", "gemma-2b-it")

    async def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(base_url=self.base_url, timeout=60.0) as client:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]