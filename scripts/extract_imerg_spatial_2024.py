import csv
import math
import re
import shutil
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from os import replace

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

BASE_URL = (
    "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/hyrax/"
    "GPM_L3/GPM_3IMERGDF.07"
)

START_DATE = date(2024, 1, 1)
END_DATE = date(2024, 12, 31)

TOKEN_FILE = Path.home() / ".earthdata_token"

WEIGHTS_FILE = (
    ROOT / "data/processed/rainfall/"
    "ballari_imerg_grid_weights.csv"
)

GRID_OUTPUT = (
    ROOT / "data/processed/rainfall/"
    "nasa_imerg_ballari_grid_2024.csv"
)

MUNICIPAL_OUTPUT = (
    ROOT / "data/processed/rainfall/"
    "nasa_imerg_ballari_municipal_2024.csv"
)

GRID_FIELDS = [
    "date", "grid_id", "latitude", "longitude",
    "precipitation_mm_per_day",
    "valid_half_hourly_retrievals",
    "intersection_area_km2", "area_weight",
    "status", "source_file",
]

MUNICIPAL_FIELDS = [
    "date", "precipitation_mm_per_day",
    "valid_grid_cells", "total_grid_cells",
    "valid_area_km2", "municipal_area_km2",
    "spatial_coverage_percent", "status", "source",
]


def parse_observation(body, cell):
    if "Dataset:" not in body:
        raise ValueError(f"Unexpected NASA response: {body[:200]}")

    lat_match = re.search(
        r"(?m)^precipitation\.lat,\s*([-+0-9.eE]+)\s*$",
        body,
    )

    lon_match = re.search(
        r"(?m)^precipitation\.precipitation"
        r"\[.*?\.lon=([-+0-9.eE]+)\],\s*"
        r"([-+0-9.eE]+|NaN)\s*$",
        body,
    )

    rainfall_match = re.search(
        r"(?m)^precipitation\.precipitation"
        r"\[.*?\],\s*([-+0-9.eE]+|NaN)\s*$",
        body,
    )

    count_match = re.search(
        r"(?m)^precipitation_cnt\.precipitation_cnt"
        r"\[.*?\],\s*([-+0-9.eE]+|NaN)\s*$",
        body,
    )

    if not all([lat_match, lon_match, rainfall_match, count_match]):
        raise ValueError("Could not parse NASA response.")

    actual_lat = float(lat_match.group(1))
    actual_lon = float(lon_match.group(1))

    if not math.isclose(
        actual_lat, float(cell["latitude"]), abs_tol=0.001
    ):
        raise ValueError(f"Latitude mismatch: {actual_lat}")

    if not math.isclose(
        actual_lon, float(cell["longitude"]), abs_tol=0.001
    ):
        raise ValueError(f"Longitude mismatch: {actual_lon}")

    rainfall = float(rainfall_match.group(1))
    count = float(count_match.group(1))

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

    # IMERG array order: time, longitude, latitude.
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
            raise ValueError(
                "Existing grid CSV has an unexpected schema. "
                "No files were modified."
            )

        for row in reader:
            day = date.fromisoformat(row["date"])
            grid_id = row["grid_id"]

            if not START_DATE <= day <= END_DATE:
                raise ValueError(f"Unexpected date in CSV: {day}")

            if grid_id not in expected_ids:
                raise ValueError(f"Unexpected grid ID: {grid_id}")

            key = (day.isoformat(), grid_id)

            if key in existing:
                raise ValueError(f"Duplicate grid observation: {key}")

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
    """Rebuild municipal records from complete four-cell dates."""

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

            # Do not calculate an estimate from an incomplete day.
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

    # Replace the municipal CSV atomically after successful writing.
    replace(temp_file, MUNICIPAL_OUTPUT)


def main():
    if not TOKEN_FILE.is_file():
        raise SystemExit("Earthdata token file not found.")

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()

    if not token:
        raise SystemExit("Earthdata token file is empty.")

    if not WEIGHTS_FILE.is_file():
        raise SystemExit("Spatial weights file not found.")

    weights = pd.read_csv(WEIGHTS_FILE)

    required = {
        "grid_id", "latitude", "longitude",
        "intersection_area_km2", "area_weight",
    }

    if required - set(weights.columns):
        raise ValueError("Spatial weights file has missing columns.")

    if weights.empty or weights["grid_id"].duplicated().any():
        raise ValueError("Empty or duplicate spatial weights.")

    if not math.isclose(
        float(weights["area_weight"].sum()), 1.0, abs_tol=1e-8
    ):
        raise ValueError("Spatial weights do not sum to 1.")

    if (weights["intersection_area_km2"] <= 0).any():
        raise ValueError("Invalid intersection area.")

    expected_ids = set(weights["grid_id"].astype(str))

    # Validate existing data BEFORE creating backups or modifying files.
    existing = load_existing_grid(expected_ids)

    backup_existing_files()

    GRID_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    if not GRID_OUTPUT.exists():
        with GRID_OUTPUT.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            csv.DictWriter(
                file, fieldnames=GRID_FIELDS
            ).writeheader()

    total_days = (END_DATE - START_DATE).days + 1
    total_expected = total_days * len(weights)

    print("\nRESUMABLE IMERG EXTRACTION")
    print("=" * 65)
    print("Existing grid observations:", len(existing))
    print("Expected observations:", total_expected)

    completed_days = {
        day for day in (
            (START_DATE + timedelta(days=i)).isoformat()
            for i in range(total_days)
        )
        if all((day, grid_id) in existing for grid_id in expected_ids)
    }

    print("Already complete days:", len(completed_days))
    print("Remaining days:", total_days - len(completed_days))

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

                if day_text in completed_days:
                    current_day += timedelta(days=1)
                    continue

                print(f"\nProcessing {day_text}")

                for _, cell in weights.iterrows():
                    grid_id = str(cell["grid_id"])
                    key = (day_text, grid_id)

                    if key in existing:
                        print("Already saved:", grid_id)
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

                        except (
                            urllib.error.URLError,
                            TimeoutError,
                            ValueError,
                            OSError,
                            UnicodeError,
                        ) as exc:
                            status = (
                                f"error: {type(exc).__name__}: {exc}"
                            )
                            print(
                                f"  Attempt {attempt + 1}/3 failed "
                                f"for {grid_id}: {status}"
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

                    writer.writerow(record)
                    file.flush()

                    existing[key] = record

                    print(
                        f"  {grid_id}: {status} "
                        f"(rainfall={rainfall}, count={count})"
                    )

                    time.sleep(0.15)

                # Rebuild municipal records after each finished day.
                all_rows = list(existing.values())
                rebuild_municipal_data(weights, all_rows)

                current_day += timedelta(days=1)

    except KeyboardInterrupt:
        print("\n\nExtraction interrupted by user.")
        print("Saved grid observations are preserved.")
        rebuild_municipal_data(weights, list(existing.values()))
        print("Municipal data rebuilt from saved grid observations.")
        print("Run this script again to resume.")
        return

    rebuild_municipal_data(weights, list(existing.values()))

    final_grid = load_existing_grid(expected_ids)

    final_complete_days = sum(
        all((day.isoformat(), grid_id) in final_grid
            for grid_id in expected_ids)
        for day in (
            START_DATE + timedelta(days=i)
            for i in range(total_days)
        )
    )

    successful = sum(
        row["status"] == "ok" for row in final_grid.values()
    )

    missing = sum(
        row["status"] in (
            "missing_or_invalid", "no_valid_retrievals"
        )
        for row in final_grid.values()
    )

    failed = sum(
        row["status"].startswith("error")
        for row in final_grid.values()
    )

    print("\nEXTRACTION CHECKPOINT")
    print("=" * 65)
    print("Grid observations saved:", len(final_grid))
    print("Expected observations:", total_expected)
    print("Complete extraction days:", final_complete_days)
    print("Successful observations:", successful)
    print("Missing/invalid observations:", missing)
    print("Failed requests:", failed)
    print("Grid output:", GRID_OUTPUT)
    print("Municipal output:", MUNICIPAL_OUTPUT)


if __name__ == "__main__":
    main()
