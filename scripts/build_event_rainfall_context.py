"""Rebuild the June 2026 rainfall context from verified source files."""

from pathlib import Path
import hashlib
import json

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]


def build():
    # Import works when launched directly from the scripts directory.
    from extract_imerg_historical_v3 import load_weights, WEIGHTS_FILE

    weights = load_weights()
    areas = weights["intersection_area_km2"].to_numpy(dtype=float)
    normalized = areas / areas.sum()
    if not np.allclose(
        weights["area_weight"].to_numpy(dtype=float),
        normalized, rtol=0, atol=1e-6,
    ):
        raise ValueError("Weights do not match intersection areas.")

    results = []
    for stamp in ("20260606", "20260607"):
        date_text = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}"
        folder = ROOT / f"data/raw/rainfall/event_{stamp}_imerg_late"
        source = folder / (
            f"3B-DAY-L.MS.MRG.3IMERG.{stamp}"
            "-S000000-E235959.V07C.nc4"
        )
        metadata = json.loads(
            (folder / "download_metadata.json").read_text(encoding="utf-8")
        )
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != metadata["sha256"]:
            raise ValueError(f"Source checksum mismatch: {date_text}")

        cells = []
        with xr.open_dataset(source) as dataset:
            if (
                dataset.sizes.get("time") != 1
                or str(dataset["time"].values[0])[:10] != date_text
                or dataset["precipitation"].attrs.get("units") != "mm/day"
            ):
                raise ValueError(f"Unexpected date or units: {date_text}")

            bounds = dataset["time_bnds"].isel(time=0).values
            start = np.datetime64(date_text, "ns")
            end = start + np.timedelta64(1, "D")
            if (
                abs(float((bounds[0] - start) / np.timedelta64(1, "s"))) > 1
                or abs(float((bounds[1] - end) / np.timedelta64(1, "s"))) > 2
            ):
                raise ValueError(f"Unexpected time bounds: {date_text}")

            for _, cell in weights.iterrows():
                point = dataset.sel(
                    lat=float(cell["latitude"]),
                    lon=float(cell["longitude"]),
                    method="nearest", tolerance=0.001,
                ).isel(time=0)

                rainfall = float(point["precipitation"].values)
                count = float(point["precipitation_cnt"].values)
                if not np.isfinite(rainfall) or rainfall < 0 or count != 48:
                    raise ValueError(
                        f"Invalid or incomplete cell: {date_text}, "
                        f"{cell['grid_id']}"
                    )

                cells.append({
                    "grid_id": str(cell["grid_id"]),
                    "precipitation_mm_per_day": rainfall,
                    "valid_half_hourly_retrievals": int(count),
                    "intersection_area_km2": float(cell["intersection_area_km2"]),
                })

        municipal = float(np.dot(
            [cell["precipitation_mm_per_day"] for cell in cells],
            normalized,
        ))
        results.append({
            "date_utc": date_text,
            "time_bounds_utc": [str(value) for value in bounds],
            "municipal_daily_mean_precipitation_rate_mm_per_day": municipal,
            "source_url": metadata["source_url"],
            "source_sha256": digest,
            "cells": cells,
        })

    return {
        "status": "satellite_rainfall_context_not_flood_validation",
        "product": "NASA GPM IMERG Late Daily V07C",
        "weights_sha256": hashlib.sha256(WEIGHTS_FILE.read_bytes()).hexdigest(),
        "municipal_intersection_area_km2": float(areas.sum()),
        "days": results,
        "approved_for_model_training": False,
        "limitations": [
            "UTC daily periods differ from Indian local calendar days.",
            "Daily averages do not reveal storm timing or peak intensity.",
            "Municipal averages do not resolve individual streets.",
            "Rainfall does not independently verify reported flooding.",
            "Late-product observations remain separate from Final training data.",
        ],
    }


def main():
    output = ROOT / (
        "data/processed/rainfall/events/"
        "ballari_imerg_late_20260606_20260607_comparison.json"
    )
    result = build()

    if output.exists():
        saved = json.loads(output.read_text(encoding="utf-8"))
        if saved != result:
            raise ValueError(
                "Rebuilt result differs from the saved analysis. "
                "Nothing overwritten; investigate the difference."
            )
        print("Saved analysis independently rebuilt: PASS")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as file:
            json.dump(result, file, indent=2, allow_nan=False)
        print("Created:", output)

    for day in result["days"]:
        value = day["municipal_daily_mean_precipitation_rate_mm_per_day"]
        print(f"{day['date_utc']}: {value:.4f} mm/day")
    print("Source hashes, dates, units, grid matching and retrieval counts: PASS")
    print("Training data and deployed model unchanged.")


if __name__ == "__main__":
    main()
