"""Training pipeline for the demand prediction model.

This module implements a complete RandomForest training pipeline:
1. Queries 15-min station_status data from CrateDB
2. Enriches with hourly weather data (join by hour)
3. Engineers features: time-of-day, day-of-week, weather, station_id
4. Creates targets at t+30min and t+60min (via time-shift)
5. Trains two RandomForest models (one per horizon)
6. Persists models and label encoder to disk

All station IDs (ACORUNA-001 to ACORUNA-015) are included in the
LabelEncoder to ensure consistency across deployments.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib


# Environment variables with defaults for Docker network
CRATEDB_HOST = os.getenv("CRATEDB_HOST", "localhost")
CRATEDB_PORT = int(os.getenv("CRATEDB_PORT", 5432))
CRATEDB_DB = os.getenv("CRATEDB_DB", "crate")
CRATEDB_USER = os.getenv("CRATEDB_USER", "crate")
CRATEDB_PASSWORD = os.getenv("CRATEDB_PASSWORD", "")

# Output directory for model artifacts
ML_DIR = Path(__file__).parent
MODEL_30_PATH = ML_DIR / "model_30.joblib"
MODEL_60_PATH = ML_DIR / "model_60.joblib"
ENCODER_PATH = ML_DIR / "label_encoder.joblib"

# All 15 stations in the system (for consistent label encoding)
ALL_STATIONS = [f"ACORUNA-{i:03d}" for i in range(1, 16)]

# RandomForest hyperparameters
RF_N_ESTIMATORS = 100
RF_RANDOM_STATE = 42

# Prediction horizons
HORIZON_30_SHIFT = -2  # 2 rows × 15min = 30min ahead
HORIZON_60_SHIFT = -4  # 4 rows × 15min = 60min ahead

# MAE warning threshold
MAE_WARNING_THRESHOLD = 3.0


def connect_cratedb() -> psycopg2.extensions.connection:
    """Connect to CrateDB using PostgreSQL wire protocol.
    
    Returns:
        psycopg2 connection object with RealDictCursor.
        
    Raises:
        psycopg2.OperationalError: If connection fails.
    """
    try:
        conn = psycopg2.connect(
            host=CRATEDB_HOST,
            port=CRATEDB_PORT,
            dbname=CRATEDB_DB,
            user=CRATEDB_USER,
            password=CRATEDB_PASSWORD,
            connect_timeout=10,
        )
        print(f"✓ Connected to CrateDB at {CRATEDB_HOST}:{CRATEDB_PORT}")
        return conn
    except psycopg2.OperationalError as e:
        print(f"✗ CrateDB connection failed: {e}")
        raise


def fetch_training_data(conn: psycopg2.extensions.connection) -> pd.DataFrame:
    """Fetch 15-min station data enriched with hourly weather.
    
    Joins etstation_status (15-min granularity) with etweatherobserved
    (hourly) by truncating station timestamps to hourly boundaries.
    
    Args:
        conn: psycopg2 connection to CrateDB.
        
    Returns:
        DataFrame with columns: time, station_id, num_bikes_available,
        wind_speed, precipitation.
        
    Raises:
        psycopg2.Error: If query fails.
    """
    query = """
    SELECT
        ss.time,
        ss.station_id,
        ss.num_bikes_available,
        wo.wind_speed,
        wo.precipitation
    FROM
        etstation_status AS ss
    INNER JOIN
        etweatherobserved AS wo
        ON DATE_TRUNC('hour', ss.time) = wo.time
    WHERE
        ss.num_bikes_available IS NOT NULL
        AND wo.wind_speed IS NOT NULL
        AND wo.precipitation IS NOT NULL
    ORDER BY
        ss.station_id, ss.time
    """
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        
        df = pd.DataFrame(rows)
        print(f"✓ Fetched {len(df):,} rows from CrateDB")
        
        if df.empty:
            raise ValueError(
                "No data returned from CrateDB. Check etstation_status "
                "and etweatherobserved tables."
            )
        
        # Ensure time column is datetime
        df["time"] = pd.to_datetime(df["time"])
        
        return df
    except psycopg2.Error as e:
        print(f"✗ Query failed: {e}")
        raise


def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, LabelEncoder]:
    """Create features from raw station and weather data.
    
    Features:
    - hour_of_day: 0-23
    - day_of_week: 0-6 (Monday=0)
    - is_weekend: True if day_of_week in {5, 6}
    - wind_speed: Direct from weather data
    - precipitation: Direct from weather data
    - station_id_encoded: Integer encoding (fitted on ALL 15 stations)
    
    Args:
        df: DataFrame with time, station_id, and weather columns.
        
    Returns:
        Tuple of (DataFrame with features, fitted LabelEncoder).
    """
    df = df.copy()
    
    # Time-based features
    df["hour_of_day"] = df["time"].dt.hour
    df["day_of_week"] = df["time"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    
    # Station ID encoding (fit on ALL stations, not just those in data)
    encoder = LabelEncoder()
    encoder.fit(ALL_STATIONS)
    df["station_id_encoded"] = encoder.transform(df["station_id"])
    
    # Select feature columns
    feature_cols = [
        "hour_of_day",
        "day_of_week",
        "is_weekend",
        "wind_speed",
        "precipitation",
        "station_id_encoded",
    ]
    
    print(f"✓ Engineered {len(feature_cols)} features")
    print(f"  - Time: hour_of_day, day_of_week, is_weekend")
    print(f"  - Weather: wind_speed, precipitation")
    print(f"  - Station: station_id_encoded (fitted on all {len(ALL_STATIONS)} stations)")
    
    return df[feature_cols], encoder


def create_targets(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create target variables by time-shifting num_bikes_available.
    
    Rows are grouped by station_id, and within each station, the
    num_bikes_available column is shifted to create two targets:
    - Target t+30min: shift -2 (2 × 15min rows = 30min ahead)
    - Target t+60min: shift -4 (4 × 15min rows = 60min ahead)
    
    Rows with NaN targets (at future boundaries) are removed.
    
    Args:
        df: DataFrame with num_bikes_available column (and station_id for grouping).
        
    Returns:
        Tuple of (features, target_30, target_60) as numpy arrays.
    """
    df = df.copy()
    
    # Group by station and apply shift within each station
    df["target_30"] = (
        df.groupby("station_id")["num_bikes_available"]
        .shift(HORIZON_30_SHIFT)
    )
    df["target_60"] = (
        df.groupby("station_id")["num_bikes_available"]
        .shift(HORIZON_60_SHIFT)
    )
    
    # Drop rows with NaN targets (future boundary rows)
    initial_rows = len(df)
    df = df.dropna(subset=["target_30", "target_60"])
    dropped = initial_rows - len(df)
    
    print(f"✓ Created targets at t+30min and t+60min")
    print(f"  - Dropped {dropped} boundary rows (NaN targets)")
    print(f"  - {len(df):,} complete training instances remaining")
    
    return df["target_30"].values, df["target_60"].values


def train_models(
    X: np.ndarray,
    y_30: np.ndarray,
    y_60: np.ndarray,
) -> tuple[RandomForestRegressor, RandomForestRegressor]:
    """Train two RandomForest models for t+30 and t+60 horizons.
    
    Uses random 80/20 train/test split. Prints MAE for each model.
    Issues warning if MAE > MAE_WARNING_THRESHOLD.
    
    Args:
        X: Feature matrix (n_samples, n_features).
        y_30: Target for t+30min.
        y_60: Target for t+60min.
        
    Returns:
        Tuple of (model_30, model_60) trained RandomForestRegressors.
    """
    # Split once, reuse for both models
    X_train, X_test, y30_train, y30_test, y60_train, y60_test = train_test_split(
        X, y_30, y_60, test_size=0.2, random_state=RF_RANDOM_STATE
    )
    
    print(f"✓ Split data: {len(X_train):,} train, {len(X_test):,} test (80/20)")
    
    # Train t+30min model
    print("\n▶ Training t+30min model...")
    model_30 = RandomForestRegressor(
        n_estimators=RF_N_ESTIMATORS,
        random_state=RF_RANDOM_STATE,
        n_jobs=-1,  # Use all cores
    )
    model_30.fit(X_train, y30_train)
    mae_30 = np.mean(np.abs(model_30.predict(X_test) - y30_test))
    print(f"  ✓ t+30min MAE on test set: {mae_30:.3f} bikes")
    if mae_30 > MAE_WARNING_THRESHOLD:
        print(f"  ⚠ WARNING: MAE > {MAE_WARNING_THRESHOLD} (model may be unreliable)")
    
    # Train t+60min model
    print("\n▶ Training t+60min model...")
    model_60 = RandomForestRegressor(
        n_estimators=RF_N_ESTIMATORS,
        random_state=RF_RANDOM_STATE,
        n_jobs=-1,
    )
    model_60.fit(X_train, y60_train)
    mae_60 = np.mean(np.abs(model_60.predict(X_test) - y60_test))
    print(f"  ✓ t+60min MAE on test set: {mae_60:.3f} bikes")
    if mae_60 > MAE_WARNING_THRESHOLD:
        print(f"  ⚠ WARNING: MAE > {MAE_WARNING_THRESHOLD} (model may be unreliable)")
    
    return model_30, model_60


def save_artifacts(
    model_30: RandomForestRegressor,
    model_60: RandomForestRegressor,
    encoder: LabelEncoder,
) -> None:
    """Persist trained models and encoder to disk.
    
    Args:
        model_30: Trained RandomForest for t+30min.
        model_60: Trained RandomForest for t+60min.
        encoder: Fitted LabelEncoder for station_id.
    """
    ML_DIR.mkdir(parents=True, exist_ok=True)
    
    joblib.dump(model_30, MODEL_30_PATH)
    print(f"✓ Saved t+30min model to {MODEL_30_PATH}")
    
    joblib.dump(model_60, MODEL_60_PATH)
    print(f"✓ Saved t+60min model to {MODEL_60_PATH}")
    
    joblib.dump(encoder, ENCODER_PATH)
    print(f"✓ Saved LabelEncoder to {ENCODER_PATH}")


def main() -> None:
    """Execute the complete training pipeline."""
    print("=" * 70)
    print("BiciCoruña Demand Prediction: Training Pipeline")
    print("=" * 70)
    
    try:
        # Step 1: Connect to CrateDB
        print("\n[1/5] Connecting to CrateDB...")
        conn = connect_cratedb()
        
        # Step 2: Fetch training data
        print("\n[2/5] Fetching training data...")
        df_raw = fetch_training_data(conn)
        conn.close()
        
        # Step 3: Engineer features
        print("\n[3/5] Engineering features...")
        X, encoder = engineer_features(df_raw)
        
        # Step 4: Create targets
        print("\n[4/5] Creating targets (time-shifted)...")
        y_30, y_60 = create_targets(df_raw)
        
        # Step 5: Train and save models
        print("\n[5/5] Training RandomForest models...")
        model_30, model_60 = train_models(X.values, y_30, y_60)
        
        # Step 6: Persist artifacts
        print("\n[6/5] Saving artifacts...")
        save_artifacts(model_30, model_60, encoder)
        
        print("\n" + "=" * 70)
        print("✓ Training complete. Models ready for inference.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Training failed: {e}", flush=True)
        raise


if __name__ == "__main__":
    main()