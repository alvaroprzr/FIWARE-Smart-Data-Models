"""Prediction helpers for station availability forecasting."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PredictionInput(BaseModel):
    # TODO: add the full feature set used by the final demand model.
    station_id: str = Field(min_length=1)
    horizon_minutes: int = Field(default=30, ge=5, le=120)
    num_bikes_available: int = Field(default=0, ge=0)


class PredictionOutput(BaseModel):
    # TODO: add confidence intervals and model provenance metadata.
    station_id: str
    horizon_minutes: int
    predicted_num_bikes_available: int


def predict_availability(payload: PredictionInput) -> PredictionOutput:
    # TODO: replace the placeholder heuristic with the trained model inference path.
    predicted = max(0, payload.num_bikes_available)
    return PredictionOutput(
        station_id=payload.station_id,
        horizon_minutes=payload.horizon_minutes,
        predicted_num_bikes_available=predicted,
    )