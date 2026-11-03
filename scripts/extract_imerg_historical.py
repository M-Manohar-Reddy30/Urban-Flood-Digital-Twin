
import csv
import math
import re
import shutil
import time
import urllib.error
import urllib.request

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

# Initial pilot: 2001 only.
START_DATE = date(2001, 1, 1)
END_DATE = date(2001, 12, 31)

TOKEN_FILE = Path.home() / ".earthdata_token"

WEIGHTS_FILE = (
    ROOT / "data/processed/rainfall/"
    "ballari_imerg_grid_weights.csv"
)

OUTPUT_DIR = ROOT / "data/processed/rainfall/historical"

GRID_OUTPUT = OUTPUT_DIR / "nasa_imerg_ballari_grid_2001.csv"
MUNICIPAL_OUTPUT = OUTPUT_DIR / "nasa_imerg_ballari_municipal_2001.csv"

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


def load_existing_grid(expected_ids):
    if not GRID_OUTPUT.exists():
        return {}

    existing = {}

    with GRID_OUTPUT.open(
        "r", newline="", encoding="utf-8"
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames != GRID_FIELDS:
            raise ValueError("Existing historical CSV schema mismatch")

        for row in reader:
            day = date.fromisoformat(row["date"])
            grid_id = row["grid_id"]

            if not START_DATE <= day <= END_DATE:
                raise ValueError(f"Unexpected date: {day}")

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


def backup_existing_files():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for path in (GRID_OUTPUT, MUNICIPAL_OUTPUT):
        if path.exists():
            backup = path.with_name(
                f"{path.stem}.backup_{timestamp}{path.suffix}"
            )
            shutil.copy2(path, backup)
            print("Backup created:", backup.name)


def rebuild_municipal_data(weights, grid_rows):
    grouped = defaultdict(list)

    for row in grid_rows:
        grouped[row["date"]].append(row)

    total_area = float(weights["intersection_area_km2"].sum())
    expected_cells = len(weights)

    temp_file = MUNICIPAL_OUTPUT.with_suffix(".csv.tmp")

    with temp_file.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=MUNICIPAL_FIELDS
        )
        writer.writeheader()

        for date_text in sorted(grouped):
            records = grouped[date_text]

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

    replace(temp_file, MUNICIPAL_OUTPUT)


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

    if required - set(weights.columns):
        raise ValueError("Spatial weights have missing columns")

    if len(weights) != 4 or weights["grid_id"].duplicated().any():
        raise ValueError("Expected exactly four unique grid cells")

    numeric = [
        "latitude",
        "longitude",
        "intersection_area_km2",
        "area_weight",
    ]

    for column in numeric:
        values = pd.to_numeric(weights[column], errors="coerce")

        if not values.map(math.isfinite).all():
            raise ValueError(f"Invalid values in {column}")

    if (weights["intersection_area_km2"] <= 0).any():
        raise ValueError("Invalid intersection area")

    if not math.isclose(
        float(weights["area_weight"].sum()), 1.0, abs_tol=1e-8
    ):
        raise ValueError("Spatial weights do not sum to 1")

    return weights


def main():
    if not TOKEN_FILE.is_file():
        raise SystemExit("Earthdata token not found")

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()

    if not token:
        raise SystemExit("Earthdata token is empty")

    weights = load_weights()
    expected_ids = set(weights["grid_id"].astype(str))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Validate existing data before backups or modifications.
    existing = load_existing_grid(expected_ids)

    backup_existing_files()

    if not GRID_OUTPUT.exists():
        with GRID_OUTPUT.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            csv.DictWriter(
                file, fieldnames=GRID_FIELDS
            ).writeheader()

    total_days = (END_DATE - START_DATE).days + 1
    expected_observations = total_days * len(weights)

    print("\nBALLARI HISTORICAL IMERG EXTRACTION")
    print("=" * 60)
    print("Period:", START_DATE, "to", END_DATE)
    print("Expected observations:", expected_observations)
    print("Existing observations:", len(existing))

    try:
        with GRID_OUTPUT.open(
            "a", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file, fieldnames=GRID_FIELDS
            )

            current_day = START_DATE

            while current_day <= END_DATE:
                day_text = current_day.isoformat()

                print("\nProcessing:", day_text)

                for _, cell in weights.iterrows():
                    grid_id = str(cell["grid_id"])
                    key = (day_text, grid_id)

                    # Existing error records are retried.
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
                                f"  Attempt {attempt + 1}/3 "
                                f"failed: {status}"
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
                        "intersection_area_km2": (
                            cell["intersection_area_km2"]
                        ),
                        "area_weight": cell["area_weight"],
                        "status": status,
                        "source_file": (
                            f"3B-DAY.MS.MRG.3IMERG."
                            f"{current_day:%Y%m%d}"
                            "-S000000-E235959.V07B.nc4"
                        ),
                    }

                    # Append only genuinely new observations.
                    if key not in existing:
                        writer.writerow(record)
                        file.flush()
                    else:
                        # Replace a previous failed record.
                        rows = [
                            row for row in existing.values()
                            if (row["date"], row["grid_id"]) != key
                        ]
                        rows.append(record)

                        temp_grid = GRID_OUTPUT.with_suffix(".csv.tmp")

                        with temp_grid.open(
                            "w", newline="", encoding="utf-8"
                        ) as temp:
                            temp_writer = csv.DictWriter(
                                temp, fieldnames=GRID_FIELDS
                            )
                            temp_writer.writeheader()
                            temp_writer.writerows(rows)

                        replace(temp_grid, GRID_OUTPUT)

                    existing[key] = record

                    print(
                        f"  {grid_id}: {status} | "
                        f"rainfall={rainfall}"
                    )

                    time.sleep(0.15)

                rebuild_municipal_data(
                    weights, list(existing.values())
                )

                current_day += timedelta(days=1)

    except KeyboardInterrupt:
        print("\nInterrupted. Saved observations are preserved.")
        rebuild_municipal_data(weights, list(existing.values()))
        print("Run this script again to resume.")
        return

    rebuild_municipal_data(weights, list(existing.values()))

    final_grid = load_existing_grid(expected_ids)

    successful = sum(
        row["status"] == "ok"
        for row in final_grid.values()
    )

    failed = sum(
        row["status"].startswith("error")
        for row in final_grid.values()
    )

    print("\nHISTORICAL EXTRACTION CHECKPOINT")
    print("=" * 60)
    print("Saved observations:", len(final_grid))
    print("Expected observations:", expected_observations)
    print("Successful observations:", successful)
    print("Failed observations:", failed)
    print("Grid CSV:", GRID_OUTPUT)
    print("Municipal CSV:", MUNICIPAL_OUTPUT)


if __name__ == "__main__":
    main()
