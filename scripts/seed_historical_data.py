#!/usr/bin/env python3
"""Seed 10 days of historical data into CrateDB for Smart Mobility Hub."""

from __future__ import annotations

import math
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Any, List, Tuple

import psycopg2
import psycopg2.extras


CRATEDB_HOST = os.environ.get("CRATEDB_HOST", "localhost")
CRATEDB_PORT = int(os.environ.get("CRATEDB_PORT", "5432"))
CRATEDB_DB = "crate"
CRATEDB_USER = "crate"
CRATEDB_PASSWORD = ""

STATIONS: List[Tuple[str, float, float, int]] = [
    ("ACORUNA-001", 43.37095, -8.39580, 20),
    ("ACORUNA-002", 43.37205, -8.39520, 18),
    ("ACORUNA-003", 43.36895, -8.39295, 16),
    ("ACORUNA-004", 43.35695, -8.40640, 22),
    ("ACORUNA-005", 43.35885, -8.40165, 17),
    ("ACORUNA-006", 43.37005, -8.39045, 15),
    ("ACORUNA-007", 43.36840, -8.39210, 19),
    ("ACORUNA-008", 43.36875, -8.40910, 24),
    ("ACORUNA-009", 43.37170, -8.41415, 21),
    ("ACORUNA-010", 43.35990, -8.41080, 23),
    ("ACORUNA-011", 43.38555, -8.40690, 15),
    ("ACORUNA-012", 43.36995, -8.39495, 16),
    ("ACORUNA-013", 43.33255, -8.40490, 25),
    ("ACORUNA-014", 43.34530, -8.41620, 18),
    ("ACORUNA-015", 43.37025, -8.40610, 20),
]

RNG = random.Random(42)           # station_status y trips
WEATHER_RNG = random.Random(42)   # weather — instancia independiente para poder regenerar por separado

EXPECTED_WEATHER_ROWS = 264  # 11 días × 24 horas


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two coordinates."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def compute_num_bikes(
    capacity: int,
    dt: datetime,
    wind_speed: float,
) -> int:
    """Compute num_bikes_available based on time of day, day of week, weather, and noise."""
    base = capacity / 2.0
    
    hour = dt.hour
    weekday = dt.weekday()  # 0=Mon, 6=Sun
    is_weekend = weekday >= 5
    
    if is_weekend:
        if 10 <= hour < 13:
            modifier = base * 0.25
        else:
            modifier = 0
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
            modifier = 0
    
    value = base + modifier
    
    if wind_speed > 8:
        value *= 0.6
    
    value += RNG.gauss(0, 1.5)
    
    return max(0, min(capacity, int(round(value))))


def generate_station_status_rows(end_date: datetime) -> List[Tuple[Any, ...]]:
    """Generate 10 days of station_status rows (15 min intervals)."""
    rows = []
    start_date = end_date - timedelta(days=10)
    current_time = start_date

    station_index = 0
    for _ in range(10 * 24 * 4 * 15):
        station_id, _, _, capacity = STATIONS[station_index % 15]
        entity_id = f"urn:ngsi-ld:station_status:acoruna:{station_id}"
        
        wind_speed = RNG.gauss(5.5, 2.5)
        wind_speed = max(0, min(18, wind_speed))
        
        num_bikes = compute_num_bikes(capacity, current_time, wind_speed)
        num_docks = capacity - num_bikes
        
        rows.append((
            current_time,
            entity_id,
            station_id,
            num_bikes,
            num_docks,
            capacity,
            True,
        ))
        
        station_index += 1
        if station_index % 15 == 0:
            current_time += timedelta(minutes=15)
    
    return rows


def generate_weather_rows(end_date: datetime) -> List[Tuple[Any, ...]]:
    """Generate 10 days of weatherobserved rows (hourly), plus one extra day so data reaches end_date."""
    rows = []
    start_date = end_date - timedelta(days=10)
    current_time = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    entity_id = "urn:ngsi-ld:WeatherObserved:acoruna:marina-001"

    for day_offset in range(11):
        current_day = start_date + timedelta(days=day_offset)
        day_of_year = current_day.timetuple().tm_yday
        month = current_day.month
        
        is_storm_day = WEATHER_RNG.random() < 0.10

        for hour in range(24):
            current_time = current_day.replace(hour=hour, minute=0, second=0, microsecond=0)

            if is_storm_day:
                wind_speed = WEATHER_RNG.uniform(11, 16)
            else:
                wind_speed = WEATHER_RNG.gauss(5.5, 2.5)
                wind_speed = max(0, min(18, wind_speed))

            wind_direction = WEATHER_RNG.randint(270, 360)

            temp_base = 13 + (3 * math.sin(2 * math.pi * (month - 1) / 12))
            temp_diurnal = 2 * math.sin(2 * math.pi * (hour - 12) / 24)
            temperature = temp_base + temp_diurnal + WEATHER_RNG.gauss(0, 0.5)

            rand_precip = WEATHER_RNG.random()
            if rand_precip < 0.70:
                precipitation = 0.0
            elif rand_precip < 0.95:
                precipitation = WEATHER_RNG.uniform(0.1, 2.0)
            else:
                precipitation = WEATHER_RNG.uniform(2.0, 8.0)
            
            rows.append((
                current_time,
                entity_id,
                temperature,
                wind_speed,
                precipitation,
                wind_direction,
            ))
    
    return rows


def generate_trips(end_date: datetime) -> List[Tuple[Any, ...]]:
    """Generate 200 trips uniformly distributed over 10 days."""
    rows = []
    start_date = end_date - timedelta(days=10)

    for trip_num in range(200):
        trip_id = f"TRIP-{trip_num:05d}"

        random_time = start_date + timedelta(
            seconds=RNG.randint(0, int(10 * 24 * 3600))
        )

        start_station_idx = RNG.randint(0, 14)
        end_station_idx = RNG.randint(0, 14)
        while end_station_idx == start_station_idx:
            end_station_idx = RNG.randint(0, 14)
        
        start_station_id = STATIONS[start_station_idx][0]
        end_station_id = STATIONS[end_station_idx][0]
        
        start_lat, start_lon = STATIONS[start_station_idx][1], STATIONS[start_station_idx][2]
        end_lat, end_lon = STATIONS[end_station_idx][1], STATIONS[end_station_idx][2]
        
        distance = haversine(start_lat, start_lon, end_lat, end_lon)
        
        duration = RNG.randint(180, 1800)
        
        rows.append((
            trip_id,
            start_station_id,
            end_station_id,
            random_time,
            random_time + timedelta(seconds=duration),
            duration,
            distance,
        ))
    
    return rows


def insert_in_batches(conn: Any, query: str, rows: List[Tuple[Any, ...]], batch_size: int = 500) -> int:
    """Insert rows in batches using executemany."""
    cursor = conn.cursor()
    inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        cursor.executemany(query, batch)
        inserted += len(batch)
    conn.commit()
    cursor.close()
    return inserted


def historical_data_already_loaded(cursor: Any) -> bool:
    """Return True when station_status and trips are already loaded.

    Weather is checked separately by weather_needs_refresh() so it can be
    refreshed independently without requiring a full reset.
    """
    for table_name in ("etstation_status", "trips"):
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        if row_count > 0:
            print(f"Datos hist\u00f3ricos ya presentes en {table_name} ({row_count} filas). Se omite el seed.")
            return True
    return False


def weather_needs_refresh(cursor: Any) -> bool:
    """Return True if weather data is missing or has fewer rows than expected."""
    cursor.execute("SELECT COUNT(*) FROM etweatherobserved")
    count = cursor.fetchone()[0]
    if count < EXPECTED_WEATHER_ROWS:
        print(f"Weather incompleto ({count}/{EXPECTED_WEATHER_ROWS} filas). Se regenera.")
        return True
    return False


def main() -> None:
    conn = psycopg2.connect(
        host=CRATEDB_HOST,
        port=CRATEDB_PORT,
        database=CRATEDB_DB,
        user=CRATEDB_USER,
        password=CRATEDB_PASSWORD,
    )
    
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS etstation_status (
            time TIMESTAMP,
            entity_id TEXT,
            station_id TEXT,
            num_bikes_available INTEGER,
            num_docks_available INTEGER,
            capacity INTEGER,
            is_renting BOOLEAN
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS etweatherobserved (
            time TIMESTAMP,
            entity_id TEXT,
            temperature REAL,
            wind_speed REAL,
            precipitation REAL,
            wind_direction INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            trip_id TEXT,
            start_station_id TEXT,
            end_station_id TEXT,
            started_at TIMESTAMP,
            ended_at TIMESTAMP,
            duration_seconds INTEGER,
            distance_meters REAL
        )
    """)
    
    conn.commit()

    if historical_data_already_loaded(cursor):
        if weather_needs_refresh(cursor):
            print("Regenerando datos de weather...")
            cursor.execute("DELETE FROM etweatherobserved")
            conn.commit()
            end_date = datetime.now(timezone.utc).replace(tzinfo=None)
            weather_rows = generate_weather_rows(end_date)
            print("Insertando weather...")
            query = """
                INSERT INTO etweatherobserved
                (time, entity_id, temperature, wind_speed, precipitation, wind_direction)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            n = insert_in_batches(conn, query, weather_rows, batch_size=500)
            print(f"  {n} filas de weather insertadas")
        cursor.close()
        conn.close()
        return

    cursor.close()
    
    end_date = datetime.now(timezone.utc).replace(tzinfo=None)
    
    print("Generando datos de station_status...")
    station_rows = generate_station_status_rows(end_date)
    
    print("Insertando station_status...")
    query = """
        INSERT INTO etstation_status
        (time, entity_id, station_id, num_bikes_available, num_docks_available, capacity, is_renting)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    insert_in_batches(conn, query, station_rows, batch_size=500)
    print(f"  {len(station_rows)} filas insertadas")
    
    print("Generando datos de weather...")
    weather_rows = generate_weather_rows(end_date)
    
    print("Insertando weather...")
    query = """
        INSERT INTO etweatherobserved
        (time, entity_id, temperature, wind_speed, precipitation, wind_direction)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    weather_inserted = insert_in_batches(conn, query, weather_rows, batch_size=500)
    
    print("Generando datos de trips...")
    trips_rows = generate_trips(end_date)
    
    print("Insertando trips...")
    query = """
        INSERT INTO trips
        (trip_id, start_station_id, end_station_id, started_at, ended_at, duration_seconds, distance_meters)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    trips_inserted = insert_in_batches(conn, query, trips_rows, batch_size=500)
    
    conn.close()
    
    print(f"Seed completado: {len(station_rows)} filas station_status, {weather_inserted} weather, {trips_inserted} trips")


if __name__ == "__main__":
    main()
