import argparse
import csv
import math
import re
import shutil
import time
import urllib.request
import numpy as np

from collections import defaultdict
from datetime import date, datetime, timedelta
from os import replace
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

BASE_URL = (
    "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/hyrax/"
    "GPM_L3/GPM_3IMERGDF.07"
)

TOKEN_FILE = Path.home() / ".earthdata_token"

WEIGHTS_FILE = (
    ROOT / "data/processed/rainfall/"
    "ballari_imerg_grid_weights.csv"
)

OUTPUT_DIR = ROOT / "data/processed/rainfall/historical"

GRID_FIELDS = [
    "date",
    "grid_id",
    "latitude",
    "longitude",
    "precipitation_mm_per_day",
    "valid_half_hourly_retrievals",
    "intersection_area_km2",
    "area_weight",
    "status",
    "source_file",
]

MUNICIPAL_FIELDS = [
    "date",
    "precipitation_mm_per_day",
    "valid_grid_cells",
    "total_grid_cells",
    "valid_area_km2",
    "municipal_area_km2",
    "spatial_coverage_percent",
    "status",
    "source",
]


def get_paths(year):
    grid = OUTPUT_DIR / f"nasa_imerg_ballari_grid_{year}.csv"
    municipal = OUTPUT_DIR / f"nasa_imerg_ballari_municipal_{year}.csv"
    return grid, municipal


def load_weights():
    if not WEIGHTS_FILE.is_file():
        raise FileNotFoundError("Spatial weights file not found")

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

    if len(weights) != 4:
        raise ValueError("Expected exactly four grid cells")

    if weights["grid_id"].isna().any() or weights["grid_id"].duplicated().any():
        raise ValueError("Grid IDs must be non-empty and unique")

    numeric = [
        "latitude",
        "longitude",
        "intersection_area_km2",
        "area_weight",
    ]

    for column in numeric:
        weights[column] = pd.to_numeric(
            weights[column], errors="coerce"
        )

        if not weights[column].map(math.isfinite).all():
            raise ValueError(f"Invalid numeric values in {column}")

    if (weights["intersection_area_km2"] <= 0).any():
        raise ValueError("Intersection areas must be positive")

    if (weights["area_weight"] <= 0).any():
        raise ValueError("Area weights must be positive")

    if not math.isclose(
        float(weights["area_weight"].sum()), 1.0, abs_tol=1e-8
    ):
        raise ValueError("Spatial weights do not sum to 1")

    return weights


def parse_observation(body, cell):
    if "Dataset:" not in body:
        raise ValueError("Unexpected NASA response")

    patterns = {
        "lat": r"(?m)^precipitation\.lat,\s*([-+0-9.eE]+)\s*$",
        "lon": (
            r"(?m)^precipitation\.precipitation"
            r"\[.*?\.lon=([-+0-9.eE]+)\],"
        ),
        "rain": (
            r"(?m)^precipitation\.precipitation"
            r"\[.*?\],\s*([-+0-9.eE]+|NaN)\s*$"
        ),
        "count": (
            r"(?m)^precipitation_cnt\.precipitation_cnt"
            r"\[.*?\],\s*([-+0-9.eE]+|NaN)\s*$"
        ),
    }

    matches = {
        name: re.search(pattern, body)
        for name, pattern in patterns.items()
    }

    if not all(matches.values()):
        raise ValueError("NASA response parsing failed")

    latitude = float(matches["lat"].group(1))
    longitude = float(matches["lon"].group(1))
    rainfall = float(matches["rain"].group(1))
    count = float(matches["count"].group(1))

    if not math.isclose(
        latitude, float(cell["latitude"]), abs_tol=0.001
    ):
        raise ValueError("Latitude mismatch")

    if not math.isclose(
        longitude, float(cell["longitude"]), abs_tol=0.001
    ):
        raise ValueError("Longitude mismatch")

    if (
        not math.isfinite(rainfall)
        or not math.isfinite(count)
        or math.isclose(rainfall, -9999.9)
        or math.isclose(count, -9999.9)
        or rainfall < 0
        or count < 0
        or count > 48
        or not count.is_integer()
    ):
        return "", "", "missing_or_invalid"

    if count == 0:
        return "", 0, "no_valid_retrievals"

    return rainfall, int(count), "ok"


def fetch_observation(day, cell, token):
    filename = (
        f"3B-DAY.MS.MRG.3IMERG.{day:%Y%m%d}"
        "-S000000-E235959.V07B.nc4"
    )

    lon_index = round(
        (float(cell["longitude"]) + 179.95) / 0.1
    )
    lat_index = round(
        (float(cell["latitude"]) + 89.95) / 0.1
    )

    constraint = (
        f"precipitation[0:1:0]"
        f"[{lon_index}:1:{lon_index}]"
        f"[{lat_index}:1:{lat_index}],"
        f"precipitation_cnt[0:1:0]"
        f"[{lon_index}:1:{lon_index}]"
        f"[{lat_index}:1:{lat_index}]"
    )

    url = (
        f"{BASE_URL}/{day.year}/{day.month:02d}/"
        f"{filename}.csv?{constraint}"
    )

    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read().decode("utf-8")

    return parse_observation(body, cell)


def backup_existing_files(paths):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    for path in paths:
        if path.exists():
            backup = path.with_name(
                f"{path.stem}.backup_{timestamp}{path.suffix}"
            )
            shutil.copy2(path, backup)
            print("Backup created:", backup.name)


def write_grid_rows_atomically(path, rows):
    temp_path = path.with_name(path.name + ".tmp")

    with temp_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=GRID_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    replace(temp_path, path)


def load_existing_grid(path, expected_ids, start_date, end_date):
    if not path.exists():
        return {}

    existing = {}

    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames != GRID_FIELDS:
            raise ValueError("Existing grid CSV schema mismatch")

        for row in reader:
            day = date.fromisoformat(row["date"])
            grid_id = row["grid_id"]

            if not start_date <= day <= end_date:
                raise ValueError(f"Unexpected date in CSV: {day}")

            if grid_id not in expected_ids:
                raise ValueError(f"Unexpected grid ID: {grid_id}")

            key = (day.isoformat(), grid_id)

            if key in existing:
                raise ValueError(f"Duplicate observation: {key}")

            if row["status"] == "ok":
                rainfall = float(row["precipitation_mm_per_day"])
                count = int(row["valid_half_hourly_retrievals"])

                if (
                    not math.isfinite(rainfall)
                    or rainfall < 0
                    or count < 1
                    or count > 48
                ):
                    raise ValueError(f"Invalid saved observation: {key}")

            existing[key] = row

    return existing


def rebuild_municipal_data(weights, grid_rows, output_path):
    grouped = defaultdict(list)

    for row in grid_rows:
        grouped[row["date"]].append(row)

    total_area = float(weights["intersection_area_km2"].sum())
    expected_cells = len(weights)

    temp_path = output_path.with_name(output_path.name + ".tmp")

    with temp_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=MUNICIPAL_FIELDS)
        writer.writeheader()

        for date_text in sorted(grouped):
            records = grouped[date_text]

            # Do not create a misleading daily estimate if a cell
            # observation is absent entirely.
            if len(records) != expected_cells:
                continue

            valid_records = [
                row for row in records if row["status"] == "ok"
            ]

            valid_area = sum(
                float(row["intersection_area_km2"])
                for row in valid_records
            )

            coverage = valid_area / total_area

            if valid_area > 0:
                rainfall = sum(
                    float(row["precipitation_mm_per_day"])
                    * float(row["intersection_area_km2"])
                    for row in valid_records
                ) / valid_area
            else:
                rainfall = ""

            if math.isclose(coverage, 1.0, abs_tol=1e-8):
                status = "complete_coverage"
            elif coverage > 0:
                status = "partial_coverage"
            else:
                status = "no_valid_coverage"

            writer.writerow({
                "date": date_text,
                "precipitation_mm_per_day": rainfall,
                "valid_grid_cells": len(valid_records),
                "total_grid_cells": expected_cells,
                "valid_area_km2": valid_area,
                "municipal_area_km2": total_area,
                "spatial_coverage_percent": coverage * 100,
                "status": status,
                "source": "NASA GPM IMERG Final Daily V07",
            })

    replace(temp_path, output_path)



def audit_year(grid_path, municipal_path, weights, year):
    grid = pd.read_csv(grid_path)
    municipal = pd.read_csv(municipal_path)

    expected_dates = set(
        pd.date_range(
            f"{year}-01-01",
            f"{year}-12-31"
        ).strftime("%Y-%m-%d")
    )

    expected_ids = set(weights["grid_id"].astype(str))
    expected_grid_rows = len(expected_dates) * len(expected_ids)

    checks = []

    def check(name, condition):
        passed = bool(condition)
        checks.append(passed)
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")

    # Grid structure
    check("Expected grid record count",
          len(grid) == expected_grid_rows)

    check("No duplicate date/grid records",
          not grid.duplicated(["date", "grid_id"]).any())

    check("Expected grid IDs",
          set(grid["grid_id"].astype(str)) == expected_ids)

    check("All calendar dates present",
          set(grid["date"]) == expected_dates)

    check("Four observations per date",
          (grid.groupby("date").size() == len(expected_ids)).all())

    # Numeric measurements
    rainfall = pd.to_numeric(
        grid["precipitation_mm_per_day"], errors="coerce"
    )

    counts = pd.to_numeric(
        grid["valid_half_hourly_retrievals"], errors="coerce"
    )

    successful = grid["status"].eq("ok")

    check("All grid observations successful",
          successful.all())

    check("Successful rainfall values finite",
          np_is_finite(rainfall[successful]))

    check("No negative successful rainfall",
          (rainfall[successful] >= 0).all())

    check("Successful retrieval counts between 1 and 48",
          counts[successful].between(1, 48).all())

    # Validate saved grid metadata against reference weights
    reference = weights[
        [
            "grid_id",
            "latitude",
            "longitude",
            "intersection_area_km2",
            "area_weight",
        ]
    ]

    metadata = grid.merge(
        reference,
        on="grid_id",
        how="left",
        suffixes=("_saved", "_reference"),
        validate="many_to_one",
    )

    metadata_ok = (
        metadata["latitude_reference"].notna().all()
        and np.allclose(
            metadata["latitude_saved"],
            metadata["latitude_reference"],
            atol=1e-6,
        )
        and np.allclose(
            metadata["longitude_saved"],
            metadata["longitude_reference"],
            atol=1e-6,
        )
        and np.allclose(
            metadata["intersection_area_km2_saved"],
            metadata["intersection_area_km2_reference"],
            atol=1e-5,
        )
        and np.allclose(
            metadata["area_weight_saved"],
            metadata["area_weight_reference"],
            atol=1e-6,
        )
    )

    check("Grid metadata matches reference weights", metadata_ok)

    # Municipal structure
    check("Municipal date coverage complete",
          set(municipal["date"]) == expected_dates)

    check("Municipal dates unique",
          not municipal["date"].duplicated().any())

    complete = municipal["status"].eq("complete_coverage")

    check("All municipal dates have complete coverage",
          complete.all())

    check("All municipal records use four valid cells",
          (municipal["valid_grid_cells"] == 4).all()
          and (municipal["total_grid_cells"] == 4).all())

    check("All municipal records report 100% coverage",
          np.allclose(
              municipal["spatial_coverage_percent"],
              100.0,
              atol=1e-6,
          ))

    # Independently recalculate area-weighted municipal rainfall
    merged = grid.merge(
        reference[["grid_id", "intersection_area_km2"]],
        on="grid_id",
        suffixes=("_saved", "_reference"),
        validate="many_to_one",
    )

    merged["rain"] = pd.to_numeric(
        merged["precipitation_mm_per_day"], errors="coerce"
    )

    merged["valid_area"] = np.where(
        merged["status"].eq("ok"),
        merged["intersection_area_km2_reference"],
        0.0,
    )

    merged["weighted_rain"] = np.where(
        merged["status"].eq("ok"),
        merged["rain"] * merged["valid_area"],
        0.0,
    )

    calculated = (
        merged.groupby("date")
        .agg(
            weighted_rain=("weighted_rain", "sum"),
            valid_area=("valid_area", "sum"),
        )
    )

    calculated["rainfall"] = (
        calculated["weighted_rain"]
        / calculated["valid_area"].replace(0, np.nan)
    )

    saved = municipal.set_index("date")

    aligned = calculated.index.equals(saved.index)

    if aligned:
        saved_rain = pd.to_numeric(
            saved["precipitation_mm_per_day"],
            errors="coerce",
        )

        difference = (
            calculated["rainfall"] - saved_rain
        ).abs()

        max_difference = difference.max()

        calculation_ok = (
            difference.notna().all()
            and max_difference <= 1e-6
        )
    else:
        max_difference = float("inf")
        calculation_ok = False

    check(
        "Municipal rainfall matches independent weighted calculation",
        calculation_ok,
    )

    print("\nGrid records:", len(grid), "/", expected_grid_rows)
    print("Municipal records:", len(municipal), "/", len(expected_dates))
    print("Successful grid observations:", int(successful.sum()))
    print("Non-successful grid observations:", int((~successful).sum()))
    print(f"Maximum municipal calculation difference: {max_difference:.12f}")
    print("Checks passed:", sum(checks), "/", len(checks))

    return all(checks)

def np_is_finite(series):
    return series.notna().all() and series.map(math.isfinite).all()


def main():
    parser = argparse.ArgumentParser(
        description="Extract Ballari historical NASA IMERG rainfall data"
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Year to extract (2001 through 2024)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the extraction plan without making NASA requests",
    )

    args = parser.parse_args()
    year = args.year

    if not 2001 <= year <= 2024:
        raise SystemExit("Supported years are 2001 through 2024")

    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)

    grid_output, municipal_output = get_paths(year)

    weights = load_weights()
    expected_ids = set(weights["grid_id"].astype(str))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    existing = load_existing_grid(
        grid_output, expected_ids, start_date, end_date
    )

    total_days = (end_date - start_date).days + 1
    expected_observations = total_days * len(weights)

    successful_existing = sum(
        row["status"] == "ok" for row in existing.values()
    )

    print("\nBALLARI HISTORICAL IMERG EXTRACTION V2")
    print("=" * 65)
    print("Year:", year)
    print("Period:", start_date, "to", end_date)
    print("Calendar days:", total_days)
    print("Grid cells:", len(weights))
    print("Expected observations:", expected_observations)
    print("Existing observations:", len(existing))
    print("Existing successful observations:", successful_existing)
    print("Observations requiring extraction/retry:",
          expected_observations - successful_existing)

    if args.dry_run:
        print("\nDRY RUN COMPLETE")
        print("No NASA requests were made.")
        print("No existing data files were modified.")
        print("Grid output:", grid_output)
        print("Municipal output:", municipal_output)
        return

    if not TOKEN_FILE.is_file():
        raise SystemExit("Earthdata token not found")

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()

    if not token:
        raise SystemExit("Earthdata token is empty")

    # Preserve existing files before any changes.
    backup_existing_files([grid_output, municipal_output])

    # Remove unsuccessful records before opening the append handle.
    # This avoids replacing a CSV while it is still open.
    successful_rows = [
        row for row in existing.values() if row["status"] == "ok"
    ]

    if len(successful_rows) != len(existing):
        write_grid_rows_atomically(grid_output, successful_rows)

    existing = {
        (row["date"], row["grid_id"]): row
        for row in successful_rows
    }

    if not grid_output.exists():
        write_grid_rows_atomically(grid_output, [])

    if not municipal_output.exists():
        rebuild_municipal_data(weights, [], municipal_output)

    current_day = start_date

    try:
        with grid_output.open(
            "a", newline="", encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(file, fieldnames=GRID_FIELDS)

            while current_day <= end_date:
                day_text = current_day.isoformat()

                print("\nProcessing:", day_text)

                for _, cell in weights.iterrows():
                    grid_id = str(cell["grid_id"])
                    key = (day_text, grid_id)

                    if key in existing and existing[key]["status"] == "ok":
                        continue

                    rainfall = ""
                    count = ""
                    status = "error"

                    for attempt in range(3):
                        try:
                            rainfall, count, status = fetch_observation(
                                current_day, cell, token
                            )
                            break

                        except KeyboardInterrupt:
                            raise

                        except Exception as exc:
                            status = (
                                f"error: {type(exc).__name__}: {exc}"
                            )

                            print(
                                f"  Attempt {attempt + 1}/3 failed: {status}"
                            )

                            if attempt < 2:
                                time.sleep(2 ** (attempt + 1))

                    record = {
                        "date": day_text,
                        "grid_id": grid_id,
                        "latitude": cell["latitude"],
                        "longitude": cell["longitude"],
                        "precipitation_mm_per_day": rainfall,
                        "valid_half_hourly_retrievals": count,
                        "intersection_area_km2": cell["intersection_area_km2"],
                        "area_weight": cell["area_weight"],
                        "status": status,
                        "source_file": (
                            f"3B-DAY.MS.MRG.3IMERG."
                            f"{current_day:%Y%m%d}"
                            "-S000000-E235959.V07B.nc4"
                        ),
                    }

                    writer.writerow(record)
                    file.flush()

                    existing[key] = record

                    print(
                        f"  {grid_id}: {status} | rainfall={rainfall}"
                    )

                    time.sleep(0.15)

                # Rebuild after each day so interruption preserves progress.
                rebuild_municipal_data(
                    weights, list(existing.values()), municipal_output
                )

                current_day += timedelta(days=1)

    except KeyboardInterrupt:
        print("\nExtraction interrupted.")
        print("Saved grid observations have been preserved.")

        rebuild_municipal_data(
            weights, list(existing.values()), municipal_output
        )

        print("Run the same year command again to resume.")
        return

    rebuild_municipal_data(
        weights, list(existing.values()), municipal_output
    )

    print("\nFINAL YEAR AUDIT")
    print("=" * 65)

    passed = audit_year(
        grid_output, municipal_output, weights, year
    )

    if passed:
        print("\nRESULT: ALL YEAR AUDIT CHECKS PASSED")
    else:
        print("\nRESULT: AUDIT INCOMPLETE OR FAILED")
        print("Inspect unsuccessful records before proceeding.")

    print("\nGrid CSV:", grid_output)
    print("Municipal CSV:", municipal_output)


if __name__ == "__main__":
    main()
