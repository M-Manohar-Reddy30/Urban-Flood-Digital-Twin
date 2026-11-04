"""Experimental one-day rainfall estimates from user-supplied history."""

from datetime import date
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import math

import joblib
import numpy as np
import pandas as pd
import sklearn
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated

router = APIRouter(
    prefix="/api/v1/rainfall",
    tags=["Experimental rainfall prediction"],
)
ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts/rainfall"
FEATURES = [
    *[f"lag_{day}" for day in range(1, 8)],
    "previous_7day_mean",
    "previous_7day_max",
    "month_sin",
    "month_cos",
]

RainfallValue = Annotated[float, Field(ge=0, le=1000)]


class PredictionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    target_date: date
    # Values must be ordered oldest first: D-7 through D-1.
    previous_7_days_mm_per_day: list[RainfallValue] = Field(
        min_length=7, max_length=7
    )


def build_features(request: PredictionInput):
    oldest_first = request.previous_7_days_mm_per_day
    latest_first = list(reversed(oldest_first))
    values = {
        f"lag_{day}": latest_first[day - 1]
        for day in range(1, 8)
    }
    angle = 2 * np.pi * (request.target_date.month - 1) / 12
    values.update({
        "previous_7day_mean": float(np.mean(oldest_first)),
        "previous_7day_max": float(max(oldest_first)),
        "month_sin": float(np.sin(angle)),
        "month_cos": float(np.cos(angle)),
    })
    return pd.DataFrame([values], columns=FEATURES)


@lru_cache(maxsize=1)
def load_model():
    metadata = json.loads(
        (ARTIFACTS / "manifest.json").read_text(encoding="utf-8")
    )
    path = ARTIFACTS / "model.joblib"
    if metadata["sklearn_version"] != sklearn.__version__:
        raise ValueError("Model runtime version mismatch.")
    if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["model_sha256"]:
        raise ValueError("Model checksum mismatch.")

    # This is the project-owned model checked against its export checksum.
    bundle = joblib.load(path)
    model = bundle["model"]
    if (
        list(bundle["features"]) != FEATURES
        or list(model.feature_names_in_) != FEATURES
        or bundle["target"] != "precipitation_mm_per_day"
    ):
        raise ValueError("Model feature contract mismatch.")
    model.set_params(n_jobs=1)
    return model


@router.post("/predict")
def predict_rainfall(request: PredictionInput):
    try:
        model = load_model()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Rainfall model is unavailable or incompatible.",
        ) from exc

    try:
        prediction = float(model.predict(build_features(request))[0])
    except (ValueError, TypeError, IndexError) as exc:
        raise HTTPException(
            status_code=500, detail="Rainfall estimation failed."
        ) from exc

    if not math.isfinite(prediction) or prediction < 0:
        raise HTTPException(
            status_code=500, detail="Invalid model output."
        )

    return {
        "status": "experimental_user_supplied_rainfall_estimate",
        "target_date": request.target_date.isoformat(),
        "prediction_mm_per_day": prediction,
        "inputs": request.model_dump(mode="json"),
        "input_order": "Oldest first: D-7 through D-1.",
        "model": "RandomForestRegressor trained on 2001-2002",
        "limitations": [
            "User-supplied preceding daily rainfall is assumed correct.",
            "Use the same municipal daily-mean rainfall-rate definition "
            "as the training data; accumulated storm depth is a different input.",
            "No live weather observations are fetched or verified.",
            "The model did not beat the zero-rainfall baseline on MAE "
            "in any evaluated period.",
            "This is an experimental rainfall estimate, not a flood prediction.",
        ],
    }
