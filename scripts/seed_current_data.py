#!/usr/bin/env python3
"""Seed current NGSI-LD data for Smart Mobility Hub in A Coruna."""

from __future__ import annotations

import copy
import json
import os
import random
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple

import requests


ORION_BASE_URL = os.environ.get("ORION_URL", "http://localhost:1026")
ENTITIES_ENDPOINT = f"{ORION_BASE_URL}/ngsi-ld/v1/entities"
FIWARE_HEADERS = {
    "Content-Type": "application/ld+json",
    "Fiware-Service": "smartmobilityhub",
    "Fiware-ServicePath": "/acoruna",
}

GBFS_CONTEXT = [
    "https://smartdatamodels.org/context.jsonld",
    "https://raw.githubusercontent.com/smart-data-models/dataModel.GBFS/master/context.jsonld",
]
WEATHER_CONTEXT = [
    "https://smart-data-models.github.io/dataModel.Weather/context.jsonld",
    "https://raw.githubusercontent.com/smart-data-models/dataModel.Weather/master/context.jsonld",
]
DEVICE_CONTEXT = [
    "https://raw.githubusercontent.com/smart-data-models/dataModel.Device/master/context.jsonld",
]
OSLO_CONTEXT = [
    "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
    "https://raw.githubusercontent.com/smart-data-models/dataModel.OSLO/master/context.jsonld",
]
OSLO_TRIP_CONTEXT = [
    "https://data.vlaanderen.be/doc/applicatieprofiel/mobiliteit-trips-en-aanbod/erkendestandaard/2020-04-23/context/mobiliteit-trips-en-aanbod-ap.jsonld",
]

NOW = datetime.now(timezone.utc)
NOW_ISO = NOW.replace(microsecond=0).isoformat().replace("+00:00", "Z")
NOW_EPOCH = int(NOW.timestamp())
CALIBRATION_ISO = "2026-04-10T10:00:00Z"
INSTALLATION_ISO = "2023-03-15T09:00:00Z"
START_DATE = "2023-03-15"

RNG = random.Random(42)


STATIONS: List[Dict[str, Any]] = [
    {
        "station_id": "ACORUNA-001",
        "name": "Praza de Maria Pita",
        "short_name": "Maria Pita",
        "lat": 43.37095,
        "lon": -8.39580,
        "address": "Praza de Maria Pita, 1, 15001 A Coruna",
        "cross_street": "Av. da Marina",
        "region_id": "acoruna-centro",
        "post_code": "15001",
        "capacity": 20,
    },
    {
        "station_id": "ACORUNA-002",
        "name": "Avenida da Marina",
        "short_name": "Marina",
        "lat": 43.37205,
        "lon": -8.39520,
        "address": "Avenida da Marina, 15001 A Coruna",
        "cross_street": "Cantones",
        "region_id": "acoruna-centro",
        "post_code": "15001",
        "capacity": 18,
    },
    {
        "station_id": "ACORUNA-003",
        "name": "Cantones",
        "short_name": "Cantones",
        "lat": 43.36895,
        "lon": -8.39295,
        "address": "Praza de Mina, 15004 A Coruna",
        "cross_street": "Xardins de Mendez Nunez",
        "region_id": "acoruna-centro",
        "post_code": "15004",
        "capacity": 16,
    },
    {
        "station_id": "ACORUNA-004",
        "name": "Cuatro Caminos",
        "short_name": "Cuatro Caminos",
        "lat": 43.35695,
        "lon": -8.40640,
        "address": "Praza de Cuatro Caminos, 15009 A Coruna",
        "cross_street": "Av. de Alfonso Molina",
        "region_id": "acoruna-ensanche",
        "post_code": "15009",
        "capacity": 22,
    },
    {
        "station_id": "ACORUNA-005",
        "name": "Linares Rivas",
        "short_name": "Linares Rivas",
        "lat": 43.35885,
        "lon": -8.40165,
        "address": "Avenida Linares Rivas, 15005 A Coruna",
        "cross_street": "Cuatro Caminos",
        "region_id": "acoruna-ensanche",
        "post_code": "15005",
        "capacity": 17,
    },
    {
        "station_id": "ACORUNA-006",
        "name": "Parrote",
        "short_name": "Parrote",
        "lat": 43.37005,
        "lon": -8.39045,
        "address": "Paseo do Parrote, 15001 A Coruna",
        "cross_street": "Porta Real",
        "region_id": "acoruna-pescaderia",
        "post_code": "15001",
        "capacity": 15,
    },
    {
        "station_id": "ACORUNA-007",
        "name": "Darsena",
        "short_name": "Darsena",
        "lat": 43.36840,
        "lon": -8.39210,
        "address": "Avenida do Porto, 15003 A Coruna",
        "cross_street": "Puerto",
        "region_id": "acoruna-pescaderia",
        "post_code": "15003",
        "capacity": 19,
    },
    {
        "station_id": "ACORUNA-008",
        "name": "Playa de Riazor",
        "short_name": "Riazor",
        "lat": 43.36875,
        "lon": -8.40910,
        "address": "Paseo Maritimo Alcalde Francisco Vazquez, 15011 A Coruna",
        "cross_street": "Praia de Riazor",
        "region_id": "acoruna-riazor",
        "post_code": "15011",
        "capacity": 24,
    },
    {
        "station_id": "ACORUNA-009",
        "name": "Estadio Riazor",
        "short_name": "Estadio",
        "lat": 43.37170,
        "lon": -8.41415,
        "address": "Rua Manuel Murguia, 44, 15011 A Coruna",
        "cross_street": "Estadio Abanca-Riazor",
        "region_id": "acoruna-riazor",
        "post_code": "15011",
        "capacity": 21,
    },
    {
        "station_id": "ACORUNA-010",
        "name": "Avenida Finisterre",
        "short_name": "Finisterre",
        "lat": 43.35990,
        "lon": -8.41080,
        "address": "Avenida Finisterre, 15010 A Coruna",
        "cross_street": "Ronda de Nelle",
        "region_id": "acoruna-agra",
        "post_code": "15010",
        "capacity": 23,
    },
    {
        "station_id": "ACORUNA-011",
        "name": "Torre de Hercules",
        "short_name": "Torre",
        "lat": 43.38555,
        "lon": -8.40690,
        "address": "Avenida Navarra, 15002 A Coruna",
        "cross_street": "Torre de Hercules",
        "region_id": "acoruna-ciudad-vieja",
        "post_code": "15002",
        "capacity": 15,
    },
    {
        "station_id": "ACORUNA-012",
        "name": "Xardin de San Carlos",
        "short_name": "San Carlos",
        "lat": 43.36995,
        "lon": -8.39495,
        "address": "Paseo Xardin de San Carlos, 15001 A Coruna",
        "cross_street": "Ciudad Vieja",
        "region_id": "acoruna-ciudad-vieja",
        "post_code": "15001",
        "capacity": 16,
    },
    {
        "station_id": "ACORUNA-013",
        "name": "Campus UDC",
        "short_name": "UDC",
        "lat": 43.33255,
        "lon": -8.40490,
        "address": "Campus de Elvina, 15008 A Coruna",
        "cross_street": "Universidade da Coruna",
        "region_id": "acoruna-monelos",
        "post_code": "15008",
        "capacity": 25,
    },
    {
        "station_id": "ACORUNA-014",
        "name": "As Conchinas",
        "short_name": "Conchinas",
        "lat": 43.34530,
        "lon": -8.41620,
        "address": "Rua As Conchinas, 15010 A Coruna",
        "cross_street": "Monelos",
        "region_id": "acoruna-monelos",
        "post_code": "15010",
        "capacity": 18,
    },
    {
        "station_id": "ACORUNA-015",
        "name": "Paseo Maritimo - Orzan",
        "short_name": "Orzan",
        "lat": 43.37025,
        "lon": -8.40610,
        "address": "Paseo Maritimo Alcalde Francisco Vazquez, 15003 A Coruna",
        "cross_street": "Playa de Orzan",
        "region_id": "acoruna-riazor",
        "post_code": "15003",
        "capacity": 20,
    },
]

FREE_BIKES: List[Dict[str, Any]] = [
    {
        "bike_id": "ACORUNA-BIKE-1001",
        "lat": 43.37090,
        "lon": -8.40935,
    },
    {
        "bike_id": "ACORUNA-BIKE-1002",
        "lat": 43.36980,
        "lon": -8.40685,
    },
    {
        "bike_id": "ACORUNA-BIKE-1003",
        "lat": 43.36795,
        "lon": -8.40475,
    },
    {
        "bike_id": "ACORUNA-BIKE-1004",
        "lat": 43.37310,
        "lon": -8.41120,
    },
    {
        "bike_id": "ACORUNA-BIKE-1005",
        "lat": 43.36685,
        "lon": -8.39895,
    },
]


def ngsi_entity(entity_id: str, entity_type: str, attributes: Dict[str, Any], context: List[str]) -> Dict[str, Any]:
    payload = {"id": entity_id, "type": entity_type}
    payload.update(attributes)
    payload["@context"] = context
    return payload


def prop(value: Any) -> Dict[str, Any]:
    return {"type": "Property", "value": value}


def prop_obs(value: Any, observed_at: str = NOW_ISO, unit_code: str | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"type": "Property", "value": value, "observedAt": observed_at}
    if unit_code:
        payload["unitCode"] = unit_code
    return payload


def attributes_only(entity: Dict[str, Any]) -> Dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in entity.items() if key not in {"id", "type"}}


def create_or_patch(entity: Dict[str, Any]) -> Tuple[bool, str]:
    entity_id = entity["id"]
    try:
        response = requests.post(
            ENTITIES_ENDPOINT,
            headers=FIWARE_HEADERS,
            data=json.dumps(entity),
            timeout=20,
        )
        if response.status_code in (201, 204):
            print(f"✓ {entity_id}")
            return True, "created"
        if response.status_code == 409:
            patch_response = requests.patch(
                f"{ENTITIES_ENDPOINT}/{entity_id}/attrs",
                headers=FIWARE_HEADERS,
                data=json.dumps(attributes_only(entity)),
                timeout=20,
            )
            if patch_response.status_code in (204, 200):
                print(f"✓ {entity_id}")
                return True, "patched"
            raise RuntimeError(
                f"PATCH {patch_response.status_code}: {patch_response.text.strip() or 'unknown error'}"
            )
        raise RuntimeError(f"POST {response.status_code}: {response.text.strip() or 'unknown error'}")
    except requests.RequestException as exc:
        print(f"✗ {entity_id}: {exc}")
        return False, str(exc)
    except RuntimeError as exc:
        print(f"✗ {entity_id}: {exc}")
        return False, str(exc)


def build_weather_observed() -> Dict[str, Any]:
    return ngsi_entity(
        "urn:ngsi-ld:WeatherObserved:acoruna:marina-001",
        "WeatherObserved",
        {
            "dateObserved": prop_obs(NOW_ISO),
            "location": {
                "type": "GeoProperty",
                "value": {"type": "Point", "coordinates": [-8.3932, 43.3718]},
            },
            "address": prop(
                {
                    "addressCountry": "ES",
                    "addressLocality": "A Coruna",
                    "addressRegion": "Galicia",
                }
            ),
            "dataProvider": prop("AEMET"),
            "source": prop("https://www.aemet.es"),
            "temperature": prop_obs(14.8, unit_code="CEL"),
            "relativeHumidity": prop_obs(0.79),
            "atmosphericPressure": prop_obs(1017.4, unit_code="HPA"),
            "precipitation": prop_obs(0.2),
            "windSpeed": prop_obs(9.6),
            "windDirection": prop_obs(310),
            "weatherType": prop("cloudy"),
            "visibility": prop("good"),
            "uVIndexMax": prop(2.0),
            "refDevice": {
                "type": "Relationship",
                "object": "urn:ngsi-ld:Device:acoruna:meteo-sensor-01",
            },
        },
        WEATHER_CONTEXT,
    )


def build_station_information() -> Dict[str, Any]:
    """Create the single station_information feed entity with all stations in data.stations[]."""
    stations_data = []
    for station in STATIONS:
        sid = station["station_id"]
        stations_data.append({
            "station_id": sid,
            "name": station["name"],
            "short_name": station["short_name"],
            "lat": station["lat"],
            "lon": station["lon"],
            "address": station["address"],
            "cross_street": station["cross_street"],
            "region_id": station["region_id"],
            "post_code": station["post_code"],
            "capacity": station["capacity"],
            "is_valet_station": False,
            "is_virtual_station": False,
            "rental_methods": ["creditcard", "phone"],
            "rental_uris": {
                "android": f"https://bicicoruna.example.com/rent/android/{sid.lower()}",
                "ios": f"https://bicicoruna.example.com/rent/ios/{sid.lower()}",
                "web": f"https://bicicoruna.example.com/rent/{sid.lower()}",
            },
        })
    return ngsi_entity(
        "urn:ngsi-ld:station_information:acoruna:bicicoruna",
        "station_information",
        {
            "last_updated": prop(NOW_EPOCH),
            "ttl": prop(30),
            "version": prop("3.0"),
            "data": prop({"stations": stations_data}),
            "refWeather": {
                "type": "Relationship",
                "object": "urn:ngsi-ld:WeatherObserved:acoruna:marina-001",
            },
        },
        GBFS_CONTEXT,
    )


def build_system_information() -> Dict[str, Any]:
    return ngsi_entity(
        "urn:ngsi-ld:system_information:acoruna:bicicoruna",
        "system_information",
        {
            "last_updated": prop(NOW_EPOCH),
            "ttl": prop(3600),
            "version": prop("3.0"),
            "data": prop({
                "system_id": "bicicoruna",
                "language": "es",
                "name": "BiciCoruna",
                "short_name": "BiciCoruna",
                "operator": "Concello de A Coruna",
                "url": "https://bicicoruna.example.com",
                "purchase_url": "https://bicicoruna.example.com/tarifas",
                "start_date": START_DATE,
                "timezone": "Europe/Madrid",
                "phone_number": "+34981000000",
                "email": "info@bicicoruna.example.com",
                "feed_contact_email": "feeds@bicicoruna.example.com",
                "license_url": "https://bicicoruna.example.com/legal/license",
            }),
        },
        GBFS_CONTEXT,
    )


def build_device_entities() -> List[Dict[str, Any]]:
    devices: List[Dict[str, Any]] = []
    for index, station in enumerate(STATIONS, start=1):
        device_id = station["station_id"]
        serial_number = f"SENSOR-{device_id}"
        battery_level = round(RNG.uniform(0.6, 1.0), 2)
        devices.append(
            ngsi_entity(
                f"urn:ngsi-ld:Device:acoruna:{device_id}",
                "Device",
                {
                    "controlledProperty": prop(["occupancy"]),
                    "deviceCategory": prop(["sensor"]),
                    "serialNumber": prop(serial_number),
                    "hardwareVersion": prop("1.0"),
                    "softwareVersion": prop("2.4.1"),
                    "firmwareVersion": prop("1.8.0"),
                    "batteryLevel": prop(battery_level),
                    "deviceState": prop("ok"),
                    "dateInstalled": prop_obs(INSTALLATION_ISO),
                    "dateLastCalibration": prop_obs(CALIBRATION_ISO),
                    "dateLastValueReported": prop_obs(NOW_ISO),
                    "location": {
                        "type": "GeoProperty",
                        "value": {"type": "Point", "coordinates": [station["lon"], station["lat"]]},
                    },
                    "refStation": {
                        "type": "Relationship",
                        "object": "urn:ngsi-ld:station_information:acoruna:bicicoruna",
                    },
                },
                DEVICE_CONTEXT,
            )
        )
    return devices


def build_station_status_entities() -> List[Dict[str, Any]]:
    statuses: List[Dict[str, Any]] = []
    for station in STATIONS:
        num_bikes_available = RNG.randint(0, station["capacity"])
        statuses.append(
            ngsi_entity(
                f"urn:ngsi-ld:station_status:acoruna:{station['station_id']}",
                "station_status",
                {
                    "last_updated": prop_obs(NOW_EPOCH),
                    "ttl": prop(30),
                    "version": prop("3.0"),
                    "station_id": prop(station["station_id"]),
                    "num_bikes_available": prop_obs(num_bikes_available),
                    "num_docks_available": prop_obs(station["capacity"] - num_bikes_available),
                    "is_installed": prop_obs(True),
                    "is_renting": prop_obs(True),
                    "is_returning": prop_obs(True),
                    "last_reported": prop_obs(NOW_EPOCH),
                    "num_bikes_disabled": prop(0),
                    "num_docks_disabled": prop(0),
                    "refStation": {
                        "type": "Relationship",
                        "object": "urn:ngsi-ld:station_information:acoruna:bicicoruna",
                    },
                },
                GBFS_CONTEXT,
            )
        )
    return statuses


def build_free_bike_status() -> Dict[str, Any]:
    bikes = []
    for bike in FREE_BIKES:
        bikes.append(
            {
                "bike_id": bike["bike_id"],
                "lat": bike["lat"],
                "lon": bike["lon"],
                "is_reserved": False,
                "is_disabled": False,
                "vehicle_type_id": "regular_bike",
                "current_range_meters": None,
                "rental_uris": {
                    "android": f"https://bicicoruna.example.com/bike/{bike['bike_id']}/android",
                    "ios": f"https://bicicoruna.example.com/bike/{bike['bike_id']}/ios",
                    "web": f"https://bicicoruna.example.com/bike/{bike['bike_id']}",
                },
            }
        )

    return ngsi_entity(
        "urn:ngsi-ld:free_bike_status:acoruna:bicicoruna",
        "free_bike_status",
        {
            "last_updated": prop_obs(NOW_EPOCH),
            "ttl": prop(30),
            "version": prop("3.0"),
            "data": prop({"bikes": bikes}),
            "refStation": {
                "type": "Relationship",
                "object": "urn:ngsi-ld:station_information:acoruna:bicicoruna",
            },
        },
        GBFS_CONTEXT,
    )


def build_mobility_station_entities() -> List[Dict[str, Any]]:
    """Create BicycleParkingStation entities (OSLO) for each station."""
    entities: List[Dict[str, Any]] = []
    for station in STATIONS:
        sid = station["station_id"]
        entities.append(
            ngsi_entity(
                f"urn:ngsi-ld:BicycleParkingStation:acoruna:{sid}",
                "BicycleParkingStation",
                {
                    "ParkingFacility.capacity": prop({
                        "type": "Capacity",
                        "Capacity.total": station["capacity"],
                    }),
                    "InfrastructureElement.geometry": prop({
                        "type": "Geometry",
                        "Geometry.asWkt": f"POINT({station['lon']} {station['lat']})",
                    }),
                    "location": {
                        "type": "GeoProperty",
                        "value": {"type": "Point", "coordinates": [station["lon"], station["lat"]]},
                    },
                    "address": prop({
                        "addressCountry": "ES",
                        "addressLocality": "A Coruna",
                        "addressRegion": "Galicia",
                        "streetAddress": station["address"],
                        "postalCode": station["post_code"],
                    }),
                    "refGBFSStation": {
                        "type": "Relationship",
                        "object": "urn:ngsi-ld:station_information:acoruna:bicicoruna",
                    },
                },
                OSLO_CONTEXT,
            )
        )
    return entities


def build_geofencing_zone() -> Dict[str, Any]:
    """Create a GBFSGeofencingZone entity covering central A Coruña."""
    return ngsi_entity(
        "urn:ngsi-ld:geofencing_zones:acoruna:bicicoruna",
        "geofencing_zones",
        {
            "last_updated": prop(NOW_EPOCH),
            "ttl": prop(300),
            "version": prop("3.0"),
            "data": prop({
                "geofencing_zones": {
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "MultiPolygon",
                                "coordinates": [
                                    [
                                        [
                                            [-8.4095, 43.3770],
                                            [-8.3880, 43.3770],
                                            [-8.3880, 43.3610],
                                            [-8.4095, 43.3610],
                                            [-8.4095, 43.3770],
                                        ]
                                    ]
                                ],
                            },
                            "properties": {
                                "name": "A Coruna zona operacional BiciCoruna",
                                "start": NOW_EPOCH,
                                "end": NOW_EPOCH + 86400 * 365,
                                "rules": [
                                    {
                                        "vehicle_type_id": ["regular bike"],
                                        "ride_allowed": True,
                                        "ride_through_allowed": True,
                                        "maximum_speed_kph": 25,
                                    }
                                ],
                            },
                        }
                    ]
                }
            }),
        },
        GBFS_CONTEXT,
    )


def build_trip_entities() -> List[Dict[str, Any]]:
    """Create a representative set of Trip entities in Orion CB (OSLO Mobility Trips AP)."""
    import datetime as _dt

    trip_pairs = [
        ("ACORUNA-001", "ACORUNA-011"),
        ("ACORUNA-002", "ACORUNA-008"),
        ("ACORUNA-003", "ACORUNA-006"),
        ("ACORUNA-007", "ACORUNA-012"),
        ("ACORUNA-004", "ACORUNA-010"),
    ]
    entities: List[Dict[str, Any]] = []
    base_time = NOW.replace(hour=8, minute=0, second=0, microsecond=0)
    for i, (origin_id, dest_id) in enumerate(trip_pairs):
        dep = base_time + _dt.timedelta(minutes=i * 20)
        arr = dep + _dt.timedelta(minutes=15 + i * 3)
        dep_iso = dep.isoformat().replace("+00:00", "Z")
        arr_iso = arr.isoformat().replace("+00:00", "Z")
        trip_id = f"urn:ngsi-ld:Trip:acoruna:{dep.strftime('%Y%m%d')}-{i+1:04d}"
        device_id = f"urn:ngsi-ld:Device:acoruna:{origin_id}"
        entities.append(
            ngsi_entity(
                trip_id,
                "Trip",
                {
                    "departureTime": prop(dep_iso),
                    "arrivalTime": prop(arr_iso),
                    "refOrigin": {
                        "type": "Relationship",
                        "object": f"urn:ngsi-ld:BicycleParkingStation:acoruna:{origin_id}",
                    },
                    "refDestination": {
                        "type": "Relationship",
                        "object": f"urn:ngsi-ld:BicycleParkingStation:acoruna:{dest_id}",
                    },
                    "refVehicle": {
                        "type": "Relationship",
                        "object": device_id,
                    },
                },
                OSLO_TRIP_CONTEXT,
            )
        )
    return entities


def seed_entities(entities: Iterable[Dict[str, Any]]) -> None:
    for entity in entities:
        create_or_patch(entity)


def main() -> None:
    entities_in_order = [
        build_weather_observed(),
        build_system_information(),
        build_station_information(),
    ]
    entities_in_order.extend(build_device_entities())
    entities_in_order.extend(build_station_status_entities())
    entities_in_order.append(build_free_bike_status())
    entities_in_order.append(build_geofencing_zone())
    entities_in_order.extend(build_mobility_station_entities())
    entities_in_order.extend(build_trip_entities())
    seed_entities(entities_in_order)


if __name__ == "__main__":
    main()