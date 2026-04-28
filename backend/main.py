"""FastAPI entrypoint for Smart Mobility Hub."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.chat import router as chat_router
from routers.stations import router as stations_router
from routers.weather import router as weather_router

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

app.include_router(stations_router, prefix="/stations", tags=["stations"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(weather_router, prefix="/weather", tags=["weather"])


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    # TODO: add dependency checks for Orion-LD, CrateDB and LM Studio.
    return {
        "status": "ok",
        "service": "smart-mobility-hub-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }