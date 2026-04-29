"""Prediction helpers for station availability forecasting.

This module provides RandomForest-based demand forecasting with fallback heuristics:

1. Models (if available):
   - Load pre-trained RandomForest models and LabelEncoder on module import
   - Extract individual tree predictions to compute confidence intervals
   - Bound predictions to [0, 25] (realistic bike capacity range)

2. Fallback (if models unavailable):
   - Per-station + per-hour mean availability from historical data
   - Narrow confidence interval (±5 bikes) for conservative estimation
   - Silent graceful degradation (no exception raised)

Singleton pattern: Models are loaded once on first import.
"""

from __future__ import annotations

import os
from pathlib import Path
import logging

import numpy as np
import psycopg2
import psycopg2.extras
from pydantic import BaseModel, Field
import joblib


logger = logging.getLogger(__name__)

# Model artifact paths
ML_DIR = Path(__file__).parent
MODEL_30_PATH = ML_DIR / "model_30.joblib"
MODEL_60_PATH = ML_DIR / "model_60.joblib"
ENCODER_PATH = ML_DIR / "label_encoder.joblib"

# Environment variables for CrateDB
CRATEDB_HOST = os.getenv("CRATEDB_HOST", "localhost")
CRATEDB_PORT = int(os.getenv("CRATEDB_PORT", 5432))
CRATEDB_DB = os.getenv("CRATEDB_DB", "crate")
CRATEDB_USER = os.getenv("CRATEDB_USER", "crate")
CRATEDB_PASSWORD = os.getenv("CRATEDB_PASSWORD", "")

# All 15 stations in the system
ALL_STATIONS = [f"ACORUNA-{i:03d}" for i in range(1, 16)]

# Prediction bounds and fallback parameters
MIN_BIKES = 0
MAX_BIKES = 25
CONFIDENCE_INTERVAL_MULTIPLIER = 1.5
FALLBACK_INTERVAL_MARGIN = 5
FALLBACK_DEFAULT_MEAN = 10

# Singleton model storage
model_30 = None
model_60 = None
label_encoder = None
models_available = False
fallback_means = {}


class PredictionInput(BaseModel):
    """Input for prediction endpoint."""
    station_id: str = Field(min_length=1)
    hour: int = Field(ge=0, le=23, description="Hour of day (0-23)")
    weekday: int = Field(ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    wind_speed: float = Field(ge=0, description="Wind speed in m/s")
    precipitation: float = Field(ge=0, description="Precipitation in mm")


class PredictionOutput(BaseModel):
    """Output with forecasts for both horizons."""
    station_id: str
    t30: dict = Field(description="t+30min forecast")
    t60: dict = Field(description="t+60min forecast")
    model_used: str = Field(description="'random_forest' or 'fallback'")


def _load_models() -> None:
    """Load pre-trained models and encoder (singleton pattern).
    
    Sets module-level variables:
    - model_30, model_60: RandomForest regressors (or None if unavailable)
    - label_encoder: LabelEncoder (or None if unavailable)
    - models_available: Boolean flag
    
    If any artifact is missing, silently sets models_available=False
    and initializes fallback means.
    """
    global model_30, model_60, label_encoder, models_available
    
    try:
        if all(path.exists() for path in [MODEL_30_PATH, MODEL_60_PATH, ENCODER_PATH]):
            model_30 = joblib.load(MODEL_30_PATH)
            model_60 = joblib.load(MODEL_60_PATH)
            label_encoder = joblib.load(ENCODER_PATH)
            models_available = True
            logger.info(f"✓ Loaded trained models from {ML_DIR}")
        else:
            missing = [p for p in [MODEL_30_PATH, MODEL_60_PATH, ENCODER_PATH] if not p.exists()]
            logger.warning(f"Model files not found: {missing}. Using fallback predictor.")
            models_available = False
    except Exception as e:
        logger.error(f"Failed to load models: {e}. Using fallback predictor.")
        models_available = False
    
    # Always initialize fallback means
    _load_fallback_means()


def _load_fallback_means() -> None:
    """Load per-station + per-hour mean availability from CrateDB.
    
    Populates fallback_means: dict[station_id][hour] -> mean_bikes
    Gracefully handles connection failures by using defaults.
    """
    global fallback_means
    
    # Initialize with defaults for all stations and hours
    fallback_means = {
        station: {hour: FALLBACK_DEFAULT_MEAN for hour in range(24)}
        for station in ALL_STATIONS
    }
    
    try:
        conn = psycopg2.connect(
            host=CRATEDB_HOST,
            port=CRATEDB_PORT,
            dbname=CRATEDB_DB,
            user=CRATEDB_USER,
            password=CRATEDB_PASSWORD,
            connect_timeout=5,
        )
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Query per-station + per-hour mean availability
        query = """
        SELECT
            station_id,
            EXTRACT(HOUR FROM time)::INT AS hour,
            AVG(num_bikes_available)::INT AS mean_bikes
        FROM
            etstation_status
        WHERE
            num_bikes_available IS NOT NULL
        GROUP BY
            station_id, EXTRACT(HOUR FROM time)
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Populate fallback_means with actual values
        for row in rows:
            station = row.get("station_id")
            hour = int(row.get("hour"))
            mean = int(row.get("mean_bikes"))
            if station in fallback_means:
                fallback_means[station][hour] = mean
        
        logger.info(f"✓ Loaded fallback means for {len(fallback_means)} stations")
    
    except Exception as e:
        logger.warning(f"Could not load fallback means from CrateDB: {e}. Using defaults.")


def _compute_confidence_interval(
    tree_predictions: np.ndarray,
) -> tuple[float, float]:
    """Compute confidence interval from individual tree predictions.
    
    Args:
        tree_predictions: Predictions from all trees in a RandomForest.
        
    Returns:
        Tuple of (low, high) bounds, clipped to [MIN_BIKES, MAX_BIKES].
    """
    mean = np.mean(tree_predictions)
    std = np.std(tree_predictions)
    low = mean - CONFIDENCE_INTERVAL_MULTIPLIER * std
    high = mean + CONFIDENCE_INTERVAL_MULTIPLIER * std
    
    # Clip to realistic bike range
    low = np.clip(low, MIN_BIKES, MAX_BIKES)
    high = np.clip(high, MIN_BIKES, MAX_BIKES)
    
    return float(low), float(high)


def predict(
    station_id: str,
    hour: int,
    weekday: int,
    wind_speed: float,
    precipitation: float,
) -> dict:
    """Forecast bike availability at a station for t+30min and t+60min.
    
    Args:
        station_id: Station identifier (e.g., 'ACORUNA-001').
        hour: Hour of day (0-23).
        weekday: Day of week (0=Monday, 6=Sunday).
        wind_speed: Wind speed in m/s.
        precipitation: Precipitation in mm.
        
    Returns:
        Dictionary with structure:
        {
            "t30": {"value": float, "low": float, "high": float},
            "t60": {"value": float, "low": float, "high": float},
            "model_used": "random_forest" | "fallback"
        }
        
    Values are clipped to [0, 25] (realistic bike capacity).
    """
    # Fallback path: no models trained yet
    if not models_available:
        mean = fallback_means.get(station_id, {}).get(hour, FALLBACK_DEFAULT_MEAN)
        low = max(MIN_BIKES, mean - FALLBACK_INTERVAL_MARGIN)
        high = min(MAX_BIKES, mean + FALLBACK_INTERVAL_MARGIN)
        
        return {
            "t30": {"value": float(mean), "low": float(low), "high": float(high)},
            "t60": {"value": float(mean), "low": float(low), "high": float(high)},
            "model_used": "fallback",
        }
    
    # Model path: use trained RandomForest
    try:
        # Prepare features (must match train.py order)
        is_weekend = 1 if weekday in [5, 6] else 0
        station_encoded = label_encoder.transform([station_id])[0]
        features = np.array([
            [hour, weekday, is_weekend, wind_speed, precipitation, station_encoded]
        ])
        
        # Get predictions from each tree (for confidence intervals)
        tree_preds_30 = np.array([
            tree.predict(features)[0] for tree in model_30.estimators_
        ])
        tree_preds_60 = np.array([
            tree.predict(features)[0] for tree in model_60.estimators_
        ])
        
        # Compute confidence intervals from tree variance
        mean_30 = np.mean(tree_preds_30)
        low_30, high_30 = _compute_confidence_interval(tree_preds_30)
        
        mean_60 = np.mean(tree_preds_60)
        low_60, high_60 = _compute_confidence_interval(tree_preds_60)
        
        # Clip all values to realistic range
        mean_30 = np.clip(mean_30, MIN_BIKES, MAX_BIKES)
        low_30 = np.clip(low_30, MIN_BIKES, MAX_BIKES)
        high_30 = np.clip(high_30, MIN_BIKES, MAX_BIKES)
        
        mean_60 = np.clip(mean_60, MIN_BIKES, MAX_BIKES)
        low_60 = np.clip(low_60, MIN_BIKES, MAX_BIKES)
        high_60 = np.clip(high_60, MIN_BIKES, MAX_BIKES)
        
        return {
            "t30": {"value": float(mean_30), "low": float(low_30), "high": float(high_30)},
            "t60": {"value": float(mean_60), "low": float(low_60), "high": float(high_60)},
            "model_used": "random_forest",
        }
    
    except Exception as e:
        # If model inference fails, fall back to historical means
        logger.error(f"Model inference failed for {station_id}: {e}. Using fallback.")
        mean = fallback_means.get(station_id, {}).get(hour, FALLBACK_DEFAULT_MEAN)
        low = max(MIN_BIKES, mean - FALLBACK_INTERVAL_MARGIN)
        high = min(MAX_BIKES, mean + FALLBACK_INTERVAL_MARGIN)
        
        return {
            "t30": {"value": float(mean), "low": float(low), "high": float(high)},
            "t60": {"value": float(mean), "low": float(low), "high": float(high)},
            "model_used": "fallback",
        }


# Load models on module import (singleton pattern)
_load_models()