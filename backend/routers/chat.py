"""Chat endpoints for the local LLM assistant."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from clients.llm import LMStudioClient

router = APIRouter()


class ChatRequest(BaseModel):
    # TODO: expand the schema with city, entity and tool-call hints.
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    # TODO: add citations and live-context metadata to the assistant response.
    answer: str


@router.post("")
async def chat(request: ChatRequest) -> ChatResponse:
    client = LMStudioClient()
    answer = await client.chat(
        [
            {"role": "system", "content": "You are the Smart Mobility Hub assistant for A Coruna."},
            {"role": "user", "content": request.message},
        ]
    )
    return ChatResponse(answer=answer)