"""FastAPI entrypoint for Smart Mobility Hub."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.chat import router as chat_router
from routers.stations import router as stations_router
from routers.weather import router as weather_router
from clients.orion import OrionClient
from clients.cratedb import CrateDBClient
import asyncio

app = FastAPI(
    title="Smart Mobility Hub API",
    version="0.1.0",
    description="NGSI-LD backend for BiciCoruna Smart in A Coruna.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGINS", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stations_router, prefix="/api/stations", tags=["stations"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(weather_router, prefix="/api/weather", tags=["weather"])


@app.get("/health", tags=["health"])
async def health() -> dict[str, object]:
    """Health endpoint: basic connectivity checks to Orion and CrateDB."""
    orion_ok = False
    cratedb_ok = False

    orion = OrionClient()
    try:
        # small probe: list entities of type station_status limit 1
        ents = await orion.get_entities("station_status")
        orion_ok = True if ents is not None else False
    except Exception:
        orion_ok = False

    cr = CrateDBClient()
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, cr.query, "SELECT 1")
        cratedb_ok = True
    except Exception:
        cratedb_ok = False

    return {
        "status": "ok",
        "service": "smart-mobility-hub-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "orion": orion_ok,
        "cratedb": cratedb_ok,
    }