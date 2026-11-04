"""Reproduce the original rainfall experiment without replacing its model."""

from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/rainfall/rainfall_experiment_wd__gq_e"
EXPERIMENT = BASE / "rf_validation_onlmhoex"


def main():
    metadata = json.loads(
        (EXPERIMENT / "experiment.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (BASE / "experiment_manifest.json").read_text(encoding="utf-8")
    )

    if sklearn.__version__ != metadata["sklearn_version"]:
        raise ValueError(
            f"Required scikit-learn: {metadata['sklearn_version']}; "
            f"installed: {sklearn.__version__}"
        )

    history_path = BASE / "municipal_rainfall_history.csv"
    actual_hash = hashlib.sha256(history_path.read_bytes()).hexdigest()
    if actual_hash != metadata["dataset_sha256"]:
        raise ValueError("Training history checksum mismatch.")

    for source in manifest["sources"]:
        source_path = ROOT / source["path"]
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if digest != source["sha256"]:
            raise ValueError(f"Source checksum mismatch: {source_path}")

    print("Original source checksums: PASS", flush=True)

    history = pd.read_csv(history_path, parse_dates=["date"])
    history = history.set_index("date").sort_index()
    if not history.index.is_unique:
        raise ValueError("Duplicate rainfall dates.")

    rain = history["precipitation_mm_per_day"]
    if not np.isfinite(rain.to_numpy(dtype=float)).all() or (rain < 0).any():
        raise ValueError("Invalid rainfall observations.")

    frame = pd.DataFrame(index=history.index)
    for day in range(1, 8):
        preceding_dates = history.index - pd.Timedelta(days=day)
        frame[f"lag_{day}"] = rain.reindex(preceding_dates).to_numpy()

    lags = frame[[f"lag_{day}" for day in range(1, 8)]]
    frame["previous_7day_mean"] = lags.mean(axis=1)
    frame["previous_7day_max"] = lags.max(axis=1)
    angle = 2 * np.pi * (frame.index.month - 1) / 12
    frame["month_sin"] = np.sin(angle)
    frame["month_cos"] = np.cos(angle)

    features = metadata["features"]
    eligible = frame[features].notna().all(axis=1)
    training = eligible & frame.index.year.isin([2001, 2002])

    if int(training.sum()) != metadata["training_rows"]:
        raise ValueError("Training row count does not match the experiment.")

    print(f"Training rows: {int(training.sum())}", flush=True)
    print("Retraining the original configuration…", flush=True)

    model = RandomForestRegressor(**metadata["parameters"])
    model.fit(frame.loc[training, features], rain.loc[training])

    saved = pd.read_csv(
        EXPERIMENT / "predictions.csv", parse_dates=["date"]
    ).set_index("date").sort_index()

    if (
        not saved.index.is_unique
        or len(saved) != metadata["validation_rows"]
        or not (saved.index.year == 2003).all()
    ):
        raise ValueError("Unexpected validation dates or row count.")

    validation = frame.reindex(saved.index)[features]
    if validation.isna().any().any():
        raise ValueError("Missing exact preceding-day observations.")

    predicted = model.predict(validation)
    expected = saved["random_forest"].to_numpy(dtype=float)

    if not np.isfinite(expected).all():
        raise ValueError("Invalid saved predictions.")

    maximum_difference = float(np.max(np.abs(predicted - expected)))
    print(f"Maximum prediction difference: {maximum_difference:.12f}")

    if not np.allclose(predicted, expected, rtol=1e-9, atol=1e-9):
        raise ValueError(
            "Retraining did not reproduce the saved predictions. "
            "Keep the existing model and investigate."
        )

    actual = rain.reindex(saved.index).to_numpy(dtype=float)
    if not np.isfinite(actual).all():
        raise ValueError("Missing validation targets.")

    print("Saved validation predictions reproduced: PASS")
    print(f"Random Forest validation MAE: {np.mean(np.abs(predicted-actual)):.6f}")
    print(f"Zero-rainfall validation MAE: {np.mean(np.abs(actual)):.6f}")
    print("Existing model and datasets were not modified.")
    print("This verifies reproducibility, not flood-prediction accuracy.")


if __name__ == "__main__":
    main()
