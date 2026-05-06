"""LM Studio / OpenAI-compatible client for chat and tool-calls."""

from __future__ import annotations

import os
from typing import Any

import httpx


class LLMClient:
    """Lightweight client compatible with OpenAI-like chat completions.

    The `chat` method returns the full JSON response so callers can inspect
    `tool_calls` / choice metadata.
    """

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("LM_STUDIO_URL", "http://host.docker.internal:1234/v1")).rstrip("/")
        self.model = model or os.getenv("LM_STUDIO_MODEL", "gemma-2b-it")

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, temperature: float = 0.2) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools is not None:
            payload["functions"] = tools

        async with httpx.AsyncClient(base_url=self.base_url, timeout=60.0) as client:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()


# Backwards-compatible alias for older code
class LMStudioClient(LLMClient):
    pass