"""CrateDB adapter for analytical queries."""

from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


class CrateDBClient:
    # TODO: add typed repository helpers for analytics and feature extraction.

    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        self.host = host or os.getenv("CRATEDB_HOST", "localhost")
        self.port = port or int(os.getenv("CRATEDB_PORT", "5432"))
        self.database = os.getenv("CRATEDB_DB", "crate")
        self.user = os.getenv("CRATEDB_USER", "crate")
        self.password = os.getenv("CRATEDB_PASSWORD", "")

    def connect(self) -> psycopg2.extensions.connection:
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
        )

    def fetch_all(self, query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        with self.connect() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                return [dict(row) for row in cursor.fetchall()]

    def query(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        """Execute a SQL query and return list of dict rows."""
        return self.fetch_all(sql, params)

    def get_station_history(self, station_id: str, hours: int = 24) -> list[dict[str, Any]]:
        """Return time series of num_bikes_available for a station during the last `hours` hours.

        The implementation assumes a table `station_status` with columns:
        - station_id
        - timestamp (or ts)
        - num_bikes_available
        Adjust if your schema differs.
        """
        sql = (
            "SELECT timestamp, num_bikes_available "
            "FROM station_status "
            "WHERE station_id = %s AND timestamp >= (NOW() - INTERVAL '%s hours') "
            "ORDER BY timestamp ASC"
        )
        return self.fetch_all(sql, (station_id, hours))

    def get_trips_heatmap(self) -> list[dict[str, Any]]:
        """Aggregate trips by start_station_id and return counts and average distance.

        Expects a `trips` table with `start_station_id`, `distance_meters` and optionally station coords in `station_information`.
        Returns items with keys: station_id, trip_count, avg_distance
        """
        sql = (
            "SELECT start_station_id AS station_id, COUNT(*) AS trip_count, AVG(distance_meters) AS avg_distance "
            "FROM trips "
            "GROUP BY start_station_id "
            "ORDER BY trip_count DESC"
        )
        rows = self.fetch_all(sql)
        # intensity: normalize by max for simple visualization
        if not rows:
            return []
        max_count = max(r.get("trip_count", 0) for r in rows) or 1
        for r in rows:
            r["intensity"] = float(r.get("trip_count", 0)) / float(max_count)
        return rows