#!/usr/bin/env python3
"""MQTT simulator for station anchor updates in BiciCoruna Smart."""

from __future__ import annotations

import json
import os
import random
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import paho.mqtt.client as mqtt


BROKER_HOST = os.getenv("MQTT_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_PORT", "1883"))
ORION_URL = os.getenv("ORION_URL", "http://localhost:1026")
PUBLISH_INTERVAL_SECONDS = 30
RNG = random.Random(42)

FALLBACK_STATIONS: List[Tuple[str, int]] = [
    (f"ACORUNA-{index:03d}", 20) for index in range(1, 16)
]


def unwrap(value):
    """Extract raw value from NGSI-LD Property wrappers when present."""
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def load_stations_from_orion() -> List[Tuple[str, int]]:
    """Load station_id and capacity from per-station station_information entities in Orion-LD."""
    endpoint = (
        f"{ORION_URL}/ngsi-ld/v1/entities"
        f"?type=station_information&limit=50&options=keyValues"
    )
    request = Request(
        endpoint,
        headers={
            "Accept": "application/ld+json",
            "Link": '<https://raw.githubusercontent.com/smart-data-models/dataModel.GBFS/master/context.jsonld>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"',
            "Fiware-Service": "smartmobilityhub",
            "Fiware-ServicePath": "/acoruna",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
        entities = json.loads(raw)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"[startup] Orion station_information unavailable, using fallback: {exc}")
        return FALLBACK_STATIONS

    if not isinstance(entities, list) or not entities:
        print("[startup] Orion returned no station_information entities, using fallback")
        return FALLBACK_STATIONS

    stations: List[Tuple[str, int]] = []
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        # station_information is a single feed entity: data.stations[] holds all stations
        data = entity.get("data", {})
        if isinstance(data, dict):
            for st in data.get("stations", []):
                if not isinstance(st, dict):
                    continue
                station_id = st.get("station_id")
                capacity_raw = st.get("capacity")
                if not station_id or capacity_raw is None:
                    continue
                try:
                    capacity = max(1, int(capacity_raw))
                except (TypeError, ValueError):
                    continue
                stations.append((str(station_id), capacity))

    if not stations:
        print("[startup] Orion returned no valid stations, using fallback")
        return FALLBACK_STATIONS

    print(f"[startup] Loaded {len(stations)} stations from Orion")
    return stations


def simulated_wind_speed() -> float:
    """Match historical seeding assumptions for wind behavior."""
    wind_speed = RNG.gauss(5.5, 2.5)
    return max(0.0, min(18.0, wind_speed))


def compute_target_bikes(capacity: int, dt: datetime, wind_speed: float) -> int:
    """Compute target bikes with the same hourly pattern as historical seed."""
    base = capacity / 2.0

    hour = dt.hour
    is_weekend = dt.weekday() >= 5

    if is_weekend:
        if 10 <= hour < 13:
            modifier = base * 0.25
        else:
            modifier = 0.0
    else:
        if 6 <= hour < 9:
            modifier = base * 0.40
        elif 12 <= hour < 14:
            modifier = base * -0.20
        elif 17 <= hour < 20:
            modifier = base * 0.35
        elif 22 <= hour or hour < 6:
            modifier = base * -0.50
        else:
            modifier = 0.0

    value = base + modifier
    if wind_speed > 8:
        value *= 0.6

    value += RNG.gauss(0, 1.5)
    return max(0, min(capacity, int(round(value))))


def apply_step_delta(previous: int, target: int, capacity: int) -> int:
    """Apply max ±1 change from previous value, biased toward target."""
    if target > previous:
        delta = RNG.choice([0, 1])
    elif target < previous:
        delta = RNG.choice([-1, 0])
    else:
        delta = RNG.choice([-1, 0, 1])

    new_value = previous + delta
    return max(0, min(capacity, new_value))


def init_state(stations: List[Tuple[str, int]]) -> Dict[str, int]:
    """Initialize station state with values approximated for current hour."""
    now = datetime.now(timezone.utc)
    state: Dict[str, int] = {}
    for station_id, capacity in stations:
        target = compute_target_bikes(capacity, now, simulated_wind_speed())
        state[station_id] = target
    return state


def build_payload(num_bikes_available: int, num_docks_available: int) -> str:
    payload = {
        "num_bikes_available": num_bikes_available,
        "num_docks_available": num_docks_available,
        "last_reported": int(time.time()),
    }
    return json.dumps(payload)


def on_connect(
    client: mqtt.Client,
    userdata,
    flags,
    reason_code,
    properties,
) -> None:
    if reason_code == 0:
        userdata["connected_event"].set()
        print(f"[mqtt] Connected to {BROKER_HOST}:{BROKER_PORT}")
    else:
        userdata["connected_event"].clear()
        print(f"[mqtt] Connection failed, reason={reason_code}")


def on_disconnect(
    client: mqtt.Client,
    userdata,
    flags,
    reason_code,
    properties,
) -> None:
    userdata["connected_event"].clear()
    print(f"[mqtt] Disconnected, reason={reason_code}. Reconnecting...")


def main() -> None:
    stations = load_stations_from_orion()
    state = init_state(stations)

    userdata = {"connected_event": threading.Event()}
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        userdata=userdata,
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect_async(BROKER_HOST, BROKER_PORT, 60)
    client.loop_start()

    try:
        while True:
            now = datetime.now(timezone.utc)
            ts = now.isoformat().replace("+00:00", "Z")

            for station_id, capacity in stations:
                wind_speed = simulated_wind_speed()
                target = compute_target_bikes(capacity, now, wind_speed)
                next_value = apply_step_delta(state[station_id], target, capacity)
                state[station_id] = next_value
                docks_available = max(0, capacity - next_value)

                topic = f"/bicicoruna/{station_id}/attrs"
                payload = build_payload(next_value, docks_available)

                if userdata["connected_event"].is_set():
                    client.publish(topic, payload, qos=0, retain=False)

                print(f"[{ts}] {station_id}: {next_value} bicis")

            time.sleep(PUBLISH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[simulator] Stopped by user")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()