"""Endpoint for triggering ML model training and reloading the predictor."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/train", tags=["ml"])
async def trigger_training() -> dict:
    """Train RandomForest demand models from CrateDB historical data.

    Runs the full training pipeline synchronously, then reloads the predictor
    singleton so subsequent /forecast calls use the new models immediately.
    """
    try:
        import ml.train as train_module
        import ml.predictor as predictor_module

        train_module.main()
        predictor_module._load_models()

        return {
            "status": "ok",
            "models": ["model_30", "model_60"],
            "model_used": "random_forest",
        }
    except Exception as exc:
        logger.error("ML training failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
