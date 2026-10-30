import csv
import importlib.util
import math
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "imerg_extractor",
    ROOT / "scripts/extract_imerg_spatial_2024.py",
)

extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)

GRID_FILE = (
    ROOT / "data/processed/rainfall/"
    "nasa_imerg_ballari_grid_2024.csv"
)

MUNICIPAL_FILE = (
    ROOT / "data/processed/rainfall/"
    "nasa_imerg_ballari_municipal_2024.csv"
)

WEIGHTS_FILE = (
    ROOT / "data/processed/rainfall/"
    "ballari_imerg_grid_weights.csv"
)

OUTPUT_FILE = (
    ROOT / "data/processed/rainfall/"
    "imerg_source_verification_report.csv"
)

DATES_TO_VERIFY = [
    date(2024, 8, 19),
    date(2024, 6, 2),
]

def main():
    token_file = Path.home() / ".earthdata_token"

    if not token_file.is_file() or not token_file.read_text().strip():
        raise SystemExit("Earthdata token missing or empty.")

    token = token_file.read_text(encoding="utf-8").strip()

    grid = pd.read_csv(GRID_FILE)
    municipal = pd.read_csv(MUNICIPAL_FILE)
    weights = pd.read_csv(WEIGHTS_FILE)

    results = []

    print("\nNASA IMERG ORIGINAL SOURCE VERIFICATION")
    print("=" * 65)

    for day in DATES_TO_VERIFY:
        day_text = day.isoformat()

        print(f"\nVerifying {day_text}")

        saved_day = grid[grid["date"] == day_text]
        saved_municipal = municipal[
            municipal["date"] == day_text
        ]

        if len(saved_day) != 4 or len(saved_municipal) != 1:
            raise ValueError(
                f"Saved dataset incomplete for {day_text}"
            )

        source_rows = []

        for _, cell in weights.iterrows():
            grid_id = str(cell["grid_id"])

            rainfall, count, status = extractor.fetch_observation(
                day, cell, token
            )

            if status != "ok":
                raise ValueError(
                    f"NASA source returned {status} "
                    f"for {day_text}, {grid_id}"
                )

            saved = saved_day[
                saved_day["grid_id"] == grid_id
            ]

            if len(saved) != 1:
                raise ValueError(
                    f"Missing or duplicate saved cell: {grid_id}"
                )

            saved = saved.iloc[0]

            rainfall_match = math.isclose(
                float(rainfall),
                float(saved["precipitation_mm_per_day"]),
                rel_tol=0,
                abs_tol=0.000001,
            )

            count_match = (
                int(count)
                == int(saved["valid_half_hourly_retrievals"])
            )

            print(
                f"{grid_id}: "
                f"source={rainfall}, "
                f"saved={saved['precipitation_mm_per_day']}, "
                f"rainfall_match={rainfall_match}, "
                f"count_match={count_match}"
            )

            if not rainfall_match or not count_match:
                raise AssertionError(
                    f"Source mismatch: {day_text}, {grid_id}"
                )

            source_rows.append({
                "grid_id": grid_id,
                "rainfall": float(rainfall),
                "area": float(cell["intersection_area_km2"]),
            })

        total_area = sum(row["area"] for row in source_rows)

        source_municipal = sum(
            row["rainfall"] * row["area"]
            for row in source_rows
        ) / total_area

        saved_value = float(
            saved_municipal.iloc[0]["precipitation_mm_per_day"]
        )

        municipal_match = math.isclose(
            source_municipal,
            saved_value,
            rel_tol=0,
            abs_tol=0.000001,
        )

        print("Source municipal estimate:", source_municipal)
        print("Saved municipal estimate:", saved_value)
        print("Municipal match:", municipal_match)

        if not municipal_match:
            raise AssertionError(
                f"Municipal source mismatch: {day_text}"
            )

        results.append({
            "date": day_text,
            "verified_grid_cells": len(source_rows),
            "rainfall_cells_match": True,
            "retrieval_counts_match": True,
            "source_municipal_rainfall_mm_per_day": source_municipal,
            "saved_municipal_rainfall_mm_per_day": saved_value,
            "municipal_match": True,
            "verification_status": "PASS",
        })

    pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False)

    print("\n" + "=" * 65)
    print("SOURCE VERIFICATION PASSED")
    print("Dates verified:", len(results))
    print("Original NASA cells verified:", len(results) * 4)
    print("Report:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
