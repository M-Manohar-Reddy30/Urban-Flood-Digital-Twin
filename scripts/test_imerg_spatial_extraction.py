from pathlib import Path

import h5py
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILE = (
    ROOT / "data/raw/rainfall/nasa_imerg/"
    "3B-DAY.MS.MRG.3IMERG.20241231-S000000-E235959.V07B.nc4"
)

WEIGHTS_FILE = (
    ROOT / "data/processed/rainfall/"
    "ballari_imerg_grid_weights.csv"
)

GRID_OUTPUT = (
    ROOT / "data/processed/rainfall/"
    "nasa_imerg_ballari_grid_20241231.csv"
)

MUNICIPAL_OUTPUT = (
    ROOT / "data/processed/rainfall/"
    "nasa_imerg_ballari_municipal_20241231.csv"
)

DATE = "2024-12-31"


def main():
    weights = pd.read_csv(WEIGHTS_FILE)

    required = {
        "grid_id",
        "latitude",
        "longitude",
        "intersection_area_km2",
        "area_weight",
    }

    missing = required - set(weights.columns)

    if missing:
        raise ValueError(f"Missing weight columns: {sorted(missing)}")

    if weights.empty:
        raise ValueError("Grid weights file is empty.")

    if not np.isclose(weights["area_weight"].sum(), 1.0):
        raise ValueError("Grid weights must sum to 1.")

    records = []

    with h5py.File(SOURCE_FILE, "r") as f:
        latitudes = f["lat"][:]
        longitudes = f["lon"][:]

        precipitation_ds = f["precipitation"]
        count_ds = f["precipitation_cnt"]

        fill_value = float(
            np.asarray(
                precipitation_ds.attrs["_FillValue"]
            ).reshape(-1)[0]
        )

        for _, cell in weights.iterrows():
            target_lat = float(cell["latitude"])
            target_lon = float(cell["longitude"])

            lat_idx = int(
                np.abs(latitudes - target_lat).argmin()
            )

            lon_idx = int(
                np.abs(longitudes - target_lon).argmin()
            )

            actual_lat = float(latitudes[lat_idx])
            actual_lon = float(longitudes[lon_idx])

            if not np.isclose(actual_lat, target_lat, atol=0.001):
                raise ValueError(
                    f"Latitude mismatch for {cell['grid_id']}"
                )

            if not np.isclose(actual_lon, target_lon, atol=0.001):
                raise ValueError(
                    f"Longitude mismatch for {cell['grid_id']}"
                )

            rainfall = float(
                precipitation_ds[0, lon_idx, lat_idx]
            )

            count = float(
                count_ds[0, lon_idx, lat_idx]
            )

            valid = (
                np.isfinite(rainfall)
                and rainfall != fill_value
                and rainfall >= 0
                and np.isfinite(count)
                and count.is_integer()
                and 0 < count <= 48
            )

            if valid:
                status = "ok"
                rainfall_value = rainfall
                retrieval_value = int(count)
            else:
                status = "missing_or_invalid"
                rainfall_value = np.nan
                retrieval_value = (
                    int(count)
                    if np.isfinite(count) and count.is_integer()
                    else np.nan
                )

            records.append({
                "date": DATE,
                "grid_id": cell["grid_id"],
                "latitude": actual_lat,
                "longitude": actual_lon,
                "precipitation_mm_per_day": rainfall_value,
                "valid_half_hourly_retrievals": retrieval_value,
                "intersection_area_km2": float(
                    cell["intersection_area_km2"]
                ),
                "area_weight": float(cell["area_weight"]),
                "status": status,
                "source_file": SOURCE_FILE.name,
            })

    grid_df = pd.DataFrame(records)

    valid_df = grid_df[grid_df["status"] == "ok"].copy()

    total_area = float(weights["intersection_area_km2"].sum())
    valid_area = float(valid_df["intersection_area_km2"].sum())

    coverage = valid_area / total_area if total_area > 0 else 0.0

    if valid_area > 0:
        municipal_rainfall = float(
            (
                valid_df["precipitation_mm_per_day"]
                * valid_df["intersection_area_km2"]
            ).sum() / valid_area
        )
    else:
        municipal_rainfall = np.nan

    municipal_status = (
        "complete_coverage"
        if np.isclose(coverage, 1.0)
        else "partial_coverage"
        if coverage > 0
        else "no_valid_coverage"
    )

    municipal_df = pd.DataFrame([{
        "date": DATE,
        "precipitation_mm_per_day": municipal_rainfall,
        "valid_grid_cells": len(valid_df),
        "total_grid_cells": len(grid_df),
        "valid_area_km2": valid_area,
        "municipal_area_km2": total_area,
        "spatial_coverage_percent": coverage * 100,
        "status": municipal_status,
        "source": "NASA GPM IMERG Final Daily V07B",
    }])

    GRID_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    grid_df.to_csv(GRID_OUTPUT, index=False)
    municipal_df.to_csv(MUNICIPAL_OUTPUT, index=False)

    print("\nFOUR-CELL EXTRACTION TEST")
    print("=" * 75)
    print(grid_df.to_string(index=False))

    print("\nMUNICIPAL RAINFALL SUMMARY")
    print("=" * 75)
    print(municipal_df.to_string(index=False))

    print("\nOUTPUT FILES")
    print(GRID_OUTPUT.relative_to(ROOT))
    print(MUNICIPAL_OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
