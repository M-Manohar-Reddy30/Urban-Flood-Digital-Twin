"""Serve saved retrospective rainfall evaluation results."""

import json
import math
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/api/v1/rainfall",
    tags=["Rainfall model evaluation"],
)

EVALUATION_FILE = (
    Path(__file__).resolve().parents[3]
    / "data/processed/rainfall/model_evaluation_v1.json"
)

METHODS = {
    "zero",
    "training_monthly_mean",
    "persistence",
    "previous_7day_mean",
    "random_forest",
}


def validate_evaluation(data):
    if not isinstance(data, dict):
        raise ValueError("Expected an object.")
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported schema.")
    if data.get("status") != "experimental_retrospective_only":
        raise ValueError("Invalid experiment status.")

    periods = data.get("periods")
    if not isinstance(periods, list) or len(periods) != 3:
        raise ValueError("Expected three evaluation periods.")

    expected = {2003: 365, 2004: 366, 2024: 359}
    seen = set()

    def finite_number(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )

    for period in periods:
        if not isinstance(period, dict):
            raise ValueError("Invalid period.")
        year = period.get("year")
        if not isinstance(year, int) or year not in expected or year in seen:
            raise ValueError("Invalid or duplicate year.")
        seen.add(year)

        records = period.get("records")
        metrics = period.get("metrics")
        if (
            period.get("days") != expected[year]
            or not isinstance(records, list)
            or len(records) != expected[year]
            or not isinstance(metrics, list)
            or len(metrics) != len(METHODS)
        ):
            raise ValueError("Invalid period counts.")

        metric_methods = set()
        for metric in metrics:
            if not isinstance(metric, dict):
                raise ValueError("Invalid metric.")
            method = metric.get("method")
            if not isinstance(method, str) or method not in METHODS:
                raise ValueError("Unknown method.")
            metric_methods.add(method)
            for key in ("mae", "rmse", "bias"):
                if not finite_number(metric.get(key)):
                    raise ValueError("Invalid metric number.")
        if metric_methods != METHODS:
            raise ValueError("Missing or duplicate methods.")

        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Invalid daily record.")
            for key in METHODS | {"precipitation_mm_per_day"}:
                value = record.get(key)
                if not finite_number(value) or value < 0:
                    raise ValueError("Invalid rainfall value.")

    # Reject non-finite numbers anywhere else in the response too.
    json.dumps(data, allow_nan=False)


@router.get("/model-evaluation")
def get_model_evaluation():
    try:
        text = EVALUATION_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail="Rainfall model evaluation is unavailable.",
        ) from exc

    try:
        data = json.loads(text)
        validate_evaluation(data)
    except (ValueError, TypeError, OverflowError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Rainfall model evaluation data is invalid.",
        ) from exc

    return data
