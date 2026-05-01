"""Chat endpoints for the local LLM assistant with function-calling integration."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from clients.llm import LLMClient
from clients.orion import OrionClient

router = APIRouter()


class ChatRequest(BaseModel):
    city: str = Field(default="acoruna")
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    response: str


async def _tool_get_station_status(station_id: str, city: str = "acoruna") -> dict[str, Any]:
    orion = OrionClient()
    eid = f"urn:ngsi-ld:station_status:{city}:{station_id}"
    return await orion.get_entity(eid)


async def _tool_get_weather(city: str) -> dict[str, Any]:
    orion = OrionClient()
    ents = await orion.get_entities("WeatherObserved", city)
    return ents[0] if ents else {}


async def _build_context_summary(city: str) -> str:
    """Build a summary of current station and weather data for the LLM context."""
    orion = OrionClient()
    parts = []

    try:
        stations = await orion.get_entities("station_information", city)
        if stations:
            data = orion.unwrap(stations[0].get("data", {}))
            if isinstance(data, dict):
                station_list = data.get("stations", [])
                parts.append(f"La ciudad tiene {len(station_list)} estaciones de BiciCoruña.")
    except Exception:
        pass

    try:
        statuses = await orion.get_entities("station_status", city)
        status_summaries = []
        for s in statuses:
            sid = orion.unwrap(s.get("station_id", ""))
            bikes = orion.unwrap(s.get("num_bikes_available", 0))
            docks = orion.unwrap(s.get("num_docks_available", 0))
            status_summaries.append(f"{sid}: {bikes} bicis, {docks} docks")
        if status_summaries:
            parts.append("Estado actual de estaciones:\n" + "\n".join(status_summaries))
    except Exception:
        pass

    try:
        weather_ents = await orion.get_entities("WeatherObserved", city)
        if weather_ents:
            w = weather_ents[0]
            temp = orion.unwrap(w.get("temperature", "N/A"))
            wind = orion.unwrap(w.get("windSpeed", "N/A"))
            precip = orion.unwrap(w.get("precipitation", "N/A"))
            parts.append(f"Clima actual: {temp}°C, viento {wind} m/s, precipitación {precip} mm")
    except Exception:
        pass

    return "\n\n".join(parts) if parts else "No se pudo obtener datos del contexto."


@router.post("")
async def chat(request: ChatRequest) -> ChatResponse:
    llm = LLMClient()

    # Define tools in OpenAI function-like schema
    tools = [
        {
            "name": "get_station_status",
            "description": "Get the current status for a station by id",
            "parameters": {"type": "object", "properties": {"station_id": {"type": "string"}}, "required": ["station_id"]},
        },
        {
            "name": "get_weather",
            "description": "Get the latest weather for a city",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        },
    ]

    # Build context from live data
    context = await _build_context_summary(request.city)

    system_msg = {
        "role": "system",
        "content": (
            f"Eres el asistente del Smart Mobility Hub para la ciudad de {request.city}. "
            f"Responde en español. Usa los datos de contexto proporcionados para dar respuestas precisas.\n\n"
            f"Datos actuales:\n{context}"
        ),
    }
    user_msg = {"role": "user", "content": request.message}

    try:
        # First LLM call
        resp = await llm.chat([system_msg, user_msg], tools=tools)

        # Inspect for tool call in a few common places
        choice = resp.get("choices", [])[0] if resp.get("choices") else {}
        msg = choice.get("message", {})

        tool_call = None
        # OpenAI style: message.get('function_call')
        if isinstance(msg, dict) and msg.get("function_call"):
            tool_call = msg.get("function_call")
        # Alternate: tool_call at top-level
        if not tool_call and choice.get("tool_call"):
            tool_call = choice.get("tool_call")

        context_text = ""
        if tool_call:
            name = tool_call.get("name")
            args_raw = tool_call.get("arguments") or "{}"
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except Exception:
                args = {}

            # Execute supported tools
            if name == "get_station_status":
                station_id = args.get("station_id")
                if not station_id:
                    raise HTTPException(status_code=400, detail="tool call missing station_id")
                result = await _tool_get_station_status(station_id, request.city)
                context_text = f"Tool get_station_status result: {json.dumps(result)}"
            elif name == "get_weather":
                city = args.get("city") or request.city
                result = await _tool_get_weather(city)
                context_text = f"Tool get_weather result: {json.dumps(result)}"
            else:
                context_text = ""

            # Second LLM call including tool result
            followup_user = {"role": "user", "content": f"Tool results:\n{context_text}\nPlease answer the original question using this live data."}
            final = await llm.chat([system_msg, user_msg, {"role": "assistant", "content": context_text}, followup_user])
            # Extract assistant content
            final_choice = final.get("choices", [])[0] if final.get("choices") else {}
            final_msg = final_choice.get("message", {})
            content = final_msg.get("content") if isinstance(final_msg, dict) else None
            if not content and final_choice.get("text"):
                content = final_choice.get("text")
            return ChatResponse(response=content or "")

        # No tool call: return assistant message content
        content = msg.get("content") if isinstance(msg, dict) else None
        if not content and choice.get("text"):
            content = choice.get("text")
        return ChatResponse(response=content or "")

    except Exception as exc:
        # LLM not available — provide a helpful response using the context data
        return ChatResponse(
            response=(
                f"El asistente IA no está disponible en este momento (LM Studio no conectado). "
                f"Aquí tienes un resumen de los datos actuales:\n\n{context}"
            )
        )