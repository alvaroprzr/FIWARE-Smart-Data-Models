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