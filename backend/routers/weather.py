"""Weather endpoints for the contextual assistant and dashboard feeds."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from clients.orion import OrionClient
from clients.cratedb import CrateDBClient

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("")
async def current_weather(city: str = Query(default="acoruna")) -> dict[str, Any]:
    """Return latest WeatherObserved attributes for `city`."""
    client = OrionClient()
    try:
        entities = await client.get_entities("WeatherObserved", city)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Orion-LD is not available for weather lookup.") from exc

    if not entities:
        return {"city": city, "items": []}

    ent = entities[0]
    # Extract common weather attributes (keyValues mode = already unwrapped)
    def _val(k: str):
        v = ent.get(k)
        if isinstance(v, dict):
            return v.get("value")
        return v

    return {
        "city": city,
        "windSpeed": _val("windSpeed"),
        "temperature": _val("temperature"),
        "precipitation": _val("precipitation"),
        "weatherType": _val("weatherType"),
    }


@router.get("/correlation")
async def weather_demand_correlation(city: str = Query(default="acoruna")) -> dict[str, Any]:
    """Return Pearson correlation coefficients between weather variables and trip demand.

    Joins hourly trip counts with weather observations and computes:
    - r(windSpeed, trips): correlation between wind speed and number of trips per hour.
    - r(precipitation, trips): correlation between precipitation and trips per hour.
    """
    client = CrateDBClient()

    def _compute() -> dict[str, Any]:
        weather_sql = (
            "SELECT DATE_TRUNC('hour', time) AS hour, AVG(wind_speed) AS wind_speed, "
            "AVG(precipitation) AS precipitation "
            "FROM etweatherobserved "
            "GROUP BY hour ORDER BY hour"
        )
        trips_sql = (
            "SELECT DATE_TRUNC('hour', started_at) AS hour, COUNT(*) AS trip_count "
            "FROM trips "
            "GROUP BY hour ORDER BY hour"
        )
        weather_rows = client.query(weather_sql)
        trips_rows = client.query(trips_sql)

        if not weather_rows or not trips_rows:
            return {"r_wind_trips": None, "r_precipitation_trips": None, "n_observations": 0}

        df_w = pd.DataFrame(weather_rows)
        df_t = pd.DataFrame(trips_rows)
        df_w["hour"] = pd.to_datetime(df_w["hour"])
        df_t["hour"] = pd.to_datetime(df_t["hour"])
        merged = pd.merge(df_w, df_t, on="hour", how="inner")

        if len(merged) < 2:
            return {"r_wind_trips": None, "r_precipitation_trips": None, "n_observations": len(merged)}

        r_wind = float(merged["wind_speed"].corr(merged["trip_count"]))
        r_precip = float(merged["precipitation"].corr(merged["trip_count"]))
        return {
            "r_wind_trips": round(r_wind, 4) if pd.notna(r_wind) else None,
            "r_precipitation_trips": round(r_precip, 4) if pd.notna(r_precip) else None,
            "n_observations": int(len(merged)),
        }

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _compute)
        return {"city": city, **result}
    except Exception as exc:
        logger.warning("Correlation computation failed: %s", exc)
        raise HTTPException(status_code=503, detail="CrateDB not available for correlation analysis.") from exc


@router.get("/trips/heatmap")
async def trips_heatmap(city: str = Query(default="acoruna")) -> list[dict[str, Any]]:
    """Return aggregated trips per origin station for heatmap visualization."""
    client = CrateDBClient()
    try:
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(None, client.get_trips_heatmap)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="CrateDB is not available for analytics.") from exc

    # Rows already contain station_id, trip_count, avg_distance, intensity
    return rows