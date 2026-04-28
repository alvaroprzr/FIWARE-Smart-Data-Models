#!/usr/bin/env python3
"""MQTT simulator for station anchor updates in BiciCoruna Smart."""

from __future__ import annotations

import json
import os
import random
import time

import paho.mqtt.client as mqtt


# TODO: replace the stub generator with the final station/state simulation rules.
BROKER_HOST = os.getenv("MQTT_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_PORT", "1883"))
STATIONS = [f"ACORUNA-{index:03d}" for index in range(1, 16)]


def build_payload(rng: random.Random) -> str:
    station_id = rng.choice(STATIONS)
    topic = f"/bicicoruna/{station_id}/attrs"
    payload = {"num_bikes_available": rng.randint(0, 20)}
    return topic, json.dumps(payload)


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.loop_start()

    rng = random.Random(42)
    try:
        while True:
            topic, payload = build_payload(rng)
            client.publish(topic, payload, qos=0, retain=False)
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()