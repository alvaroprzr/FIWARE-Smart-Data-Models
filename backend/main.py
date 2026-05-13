"""FastAPI entrypoint for Smart Mobility Hub."""

from __future__ import annotations

import logging
import math
import os
import random
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.chat import router as chat_router
from routers.stations import router as stations_router
from routers.weather import router as weather_router
from routers.alerts import router as alerts_router
from routers.train import router as train_router
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
app.include_router(train_router, prefix="/api", tags=["ml"])


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


_LIVE_STATIONS = [
    ("ACORUNA-001", 43.37095, -8.39580), ("ACORUNA-002", 43.37205, -8.39520),
    ("ACORUNA-003", 43.36895, -8.39295), ("ACORUNA-004", 43.35695, -8.40640),
    ("ACORUNA-005", 43.35885, -8.40165), ("ACORUNA-006", 43.37005, -8.39045),
    ("ACORUNA-007", 43.36840, -8.39210), ("ACORUNA-008", 43.36875, -8.40910),
    ("ACORUNA-009", 43.37170, -8.41415), ("ACORUNA-010", 43.35990, -8.41080),
    ("ACORUNA-011", 43.38555, -8.40690), ("ACORUNA-012", 43.36995, -8.39495),
    ("ACORUNA-013", 43.33255, -8.40490), ("ACORUNA-014", 43.34530, -8.41620),
    ("ACORUNA-015", 43.37025, -8.40610),
]

_TRIP_INSERT = (
    "INSERT INTO crate.trips "
    "(trip_id, start_station_id, end_station_id, started_at, ended_at, duration_seconds, distance_meters) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)

_trip_logger = logging.getLogger("trip_generator")


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = math.sin(math.radians(lat2 - lat1) / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _make_trip_row(started_at: datetime) -> tuple:
    a = random.randint(0, 14)
    b = random.randint(0, 14)
    while b == a:
        b = random.randint(0, 14)
    sid_a, la, lo_a = _LIVE_STATIONS[a]
    sid_b, lb, lo_b = _LIVE_STATIONS[b]
    dist = _haversine_m(la, lo_a, lb, lo_b)
    dur = random.randint(180, 1800)
    trip_id = f"TRIP-LIVE-{int(started_at.timestamp() * 1000)}-{a}{b}"
    return (trip_id, sid_a, sid_b, started_at, started_at + timedelta(seconds=dur), dur, dist)


async def _trip_generator_loop() -> None:
    await asyncio.sleep(20)  # allow DB to be ready
    cr = CrateDBClient()
    loop = asyncio.get_running_loop()

    # Catch-up: fill the gap between the last seeded trip and now
    try:
        rows = await loop.run_in_executor(None, cr.query, "SELECT MAX(started_at) AS max_at FROM crate.trips")
        raw = rows[0]["max_at"] if rows and rows[0]["max_at"] is not None else None
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if raw is not None:
            last_dt = raw.replace(tzinfo=None) if isinstance(raw, datetime) else datetime.fromtimestamp(raw / 1000, tz=timezone.utc).replace(tzinfo=None)
            gap = (now - last_dt).total_seconds()
            if gap > 300:
                n = max(1, int(gap / 900))  # ~4 trips per hour
                for i in range(n):
                    t = last_dt + timedelta(seconds=(i + 1) * gap / (n + 1))
                    await loop.run_in_executor(None, cr.execute, _TRIP_INSERT, _make_trip_row(t))
                _trip_logger.info("Catch-up: inserted %d trips (gap %.0f min)", n, gap / 60)
    except Exception as exc:
        _trip_logger.warning("Catch-up failed: %s", exc)

    # Steady-state: one synthetic trip every 10 minutes
    while True:
        await asyncio.sleep(600)
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            row = _make_trip_row(now - timedelta(seconds=random.randint(0, 120)))
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, cr.execute, _TRIP_INSERT, row)
            _trip_logger.info("Live trip: %s", row[0])
        except Exception as exc:
            _trip_logger.warning("Trip insert error: %s", exc)


@app.on_event("startup")
async def start_trip_generator() -> None:
    asyncio.create_task(_trip_generator_loop())


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