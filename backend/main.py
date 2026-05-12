"""FastAPI entrypoint for Smart Mobility Hub."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.chat import router as chat_router
from routers.stations import router as stations_router
from routers.weather import router as weather_router
from routers.alerts import router as alerts_router
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
app.include_router(alerts_router, prefix="/api/alerts", tags=["alerts"])


@app.on_event("startup")
async def ensure_orion_subscriptions() -> None:
    """Create required Orion-LD subscriptions (QuantumLeap persistence + backend notify).

    This runs at startup and attempts to create idempotent subscriptions. It will
    ignore 'already exists' responses.
    """
    import os
    import logging

    logger = logging.getLogger("startup")
    orion = OrionClient()

    # QuantumLeap notify endpoint (for historical persistence)
    ql_base = os.getenv("QUANTUMLEAP_URL", "http://quantumleap:8668")
    ql_endpoint = ql_base.rstrip("/") + "/v2/notify"

    # Backend notify endpoint to receive Orion notifications for alerts
    backend_notify = os.getenv("BACKEND_NOTIFY_URL", "http://fastapi-backend:8000/api/alerts/notify")

    subs = [
        {
            "id": "urn:ngsi-ld:Subscription:station_status_to_quantumleap",
            "type": "Subscription",
            "name": "station_status_changes_to_quantumleap",
            "entities": [{"type": "station_status"}],
            "watchedAttributes": ["num_bikes_available", "num_docks_available", "is_renting", "is_returning", "last_reported"],
            "notification": {"attributes": ["num_bikes_available", "num_docks_available", "is_renting", "is_returning", "last_reported", "refStation"], "endpoint": {"uri": ql_endpoint, "accept": "application/json"}},
            "throttling": 1,
            "@context": ["https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld", "https://raw.githubusercontent.com/smart-data-models/dataModel.GBFS/master/context.jsonld"]
        },
        {
            "id": "urn:ngsi-ld:Subscription:weatherobserved_to_quantumleap",
            "type": "Subscription",
            "name": "weatherobserved_changes_to_quantumleap",
            "entities": [{"type": "WeatherObserved"}],
            "watchedAttributes": ["temperature", "windSpeed", "dateObserved"],
            "notification": {"attributes": ["temperature", "windSpeed", "dateObserved", "location", "refDevice"], "endpoint": {"uri": ql_endpoint, "accept": "application/json"}},
            "throttling": 5,
            "@context": ["https://smartdatamodels.org/context.jsonld", "https://raw.githubusercontent.com/smart-data-models/dataModel.Weather/master/context.jsonld"]
        },
        {
            "id": "urn:ngsi-ld:Subscription:trip_to_quantumleap",
            "type": "Subscription",
            "name": "trip_changes_to_quantumleap",
            "entities": [{"type": "Trip"}],
            "watchedAttributes": ["departureTime", "arrivalTime", "refOrigin", "refDestination"],
            "notification": {"attributes": ["departureTime", "arrivalTime", "refOrigin", "refDestination"], "endpoint": {"uri": ql_endpoint, "accept": "application/json"}},
            "throttling": 5,
            "@context": ["https://data.vlaanderen.be/doc/applicatieprofiel/mobiliteit-trips-en-aanbod/erkendestandaard/2020-04-23/context/mobiliteit-trips-en-aanbod-ap.jsonld"]
        },
        # Orion -> backend notify for alerts on station_status
        {
            "id": "urn:ngsi-ld:Subscription:station_status_to_backend_alerts",
            "type": "Subscription",
            "name": "station_status_changes_to_backend_alerts",
            "entities": [{"type": "station_status"}],
            "watchedAttributes": ["num_bikes_available", "num_docks_available", "last_reported"],
            "notification": {"attributes": ["num_bikes_available", "num_docks_available", "last_reported", "refStation"], "endpoint": {"uri": backend_notify, "accept": "application/json"}},
            "throttling": 1,
            "@context": ["https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld", "https://raw.githubusercontent.com/smart-data-models/dataModel.GBFS/master/context.jsonld"]
        }
    ]

    for sub in subs:
        try:
            await orion.create_subscription(sub)
            logger.info("Ensured subscription %s", sub.get("id"))
        except Exception as exc:
            logger.warning("Could not ensure subscription %s: %s", sub.get("id"), exc)


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