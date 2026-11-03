
import math
import re
import urllib.request
from datetime import date
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

DATA_DIR = ROOT / "data/processed/rainfall/historical"

GRID_FILE = DATA_DIR / "nasa_imerg_ballari_grid_2003.csv"
MUNICIPAL_FILE = DATA_DIR / "nasa_imerg_ballari_municipal_2003.csv"

TEST_DATES = [
    date(2003, 10, 20),
    date(2003, 8, 22),
]


def fetch_and_validate_observation(day, cell, token):

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

    patterns = {
        "lat": (
            r"(?m)^precipitation\.lat,\s*"
            r"([-+0-9.eE]+)\s*$"
        ),
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

    lat = float(matches["lat"].group(1))
    lon = float(matches["lon"].group(1))
    rainfall = float(matches["rain"].group(1))
    count = float(matches["count"].group(1))

    if not math.isclose(
        lat, float(cell["latitude"]), abs_tol=0.001
    ):
        raise ValueError("Latitude mismatch")

    if not math.isclose(
        lon, float(cell["longitude"]), abs_tol=0.001
    ):
        raise ValueError("Longitude mismatch")

    if (
        not math.isfinite(rainfall)
        or not math.isfinite(count)
        or rainfall == -9999.9
        or count == -9999.9
        or rainfall < 0
        or count < 0
        or count > 48
        or not count.is_integer()
    ):
        raise ValueError("Invalid rainfall or retrieval count")

    return rainfall, int(count)


def main():

    if not TOKEN_FILE.is_file():
        raise SystemExit("Earthdata token not found")

    if not WEIGHTS_FILE.is_file():
        raise SystemExit("Spatial weights file not found")

    if not GRID_FILE.is_file():
        raise SystemExit("2002 grid CSV not found")

    if not MUNICIPAL_FILE.is_file():
        raise SystemExit("2001 municipal CSV not found")

    token = TOKEN_FILE.read_text(
        encoding="utf-8"
    ).strip()

    if not token:
        raise SystemExit("Earthdata token is empty")

    weights = pd.read_csv(WEIGHTS_FILE)

    saved_grid = pd.read_csv(GRID_FILE)
    saved_municipal = pd.read_csv(MUNICIPAL_FILE)

    saved_grid["date"] = pd.to_datetime(
        saved_grid["date"]
    ).dt.date

    saved_municipal["date"] = pd.to_datetime(
        saved_municipal["date"]
    ).dt.date

    if weights["grid_id"].duplicated().any():
        raise SystemExit("Duplicate grid IDs in weights file")

    if set(saved_grid["status"]) != {"ok"}:
        raise SystemExit("Grid CSV contains non-OK records")

    if not saved_grid["date"].isin(TEST_DATES).any():
        raise SystemExit("No requested test dates found in grid CSV")

    print("NASA SOURCE-TO-CSV HISTORICAL VERIFICATION")
    print("=" * 70)

    passed = 0
    failed = 0

    for day in TEST_DATES:

        print(f"\nDate: {day}")

        nasa_weighted_values = []
        day_failed = False

        for _, cell in weights.iterrows():

            try:

                rainfall, count = fetch_and_validate_observation(
                    day, cell, token
                )

                saved = saved_grid[
                    (saved_grid["date"] == day)
                    & (
                        saved_grid["grid_id"]
                        == cell["grid_id"]
                    )
                ]

                if len(saved) != 1:
                    raise ValueError(
                        "Expected exactly one saved grid record"
                    )

                saved_rain = float(
                    saved.iloc[0]["precipitation_mm_per_day"]
                )

                saved_count = int(
                    saved.iloc[0]["valid_half_hourly_retrievals"]
                )

                matches = (
                    math.isclose(
                        rainfall, saved_rain, abs_tol=1e-6
                    )
                    and count == saved_count
                )

                if not matches:
                    raise ValueError(
                        f"NASA={rainfall}/{count}, "
                        f"saved={saved_rain}/{saved_count}"
                    )

                nasa_weighted_values.append(
                    rainfall * float(cell["area_weight"])
                )

                passed += 1

                print(
                    f"  {cell['grid_id']}: PASS | "
                    f"NASA={rainfall} | "
                    f"Saved={saved_rain} | "
                    f"Retrievals={count}"
                )

            except Exception as exc:

                failed += 1
                day_failed = True

                print(
                    f"  {cell['grid_id']}: FAILED | "
                    f"{type(exc).__name__}: {exc}"
                )

        # Verify the municipal weighted rainfall
        if not day_failed and len(nasa_weighted_values) == len(weights):

            nasa_municipal = sum(nasa_weighted_values)

            saved_row = saved_municipal[
                saved_municipal["date"] == day
            ]

            if len(saved_row) == 1:

                saved_value = float(
                    saved_row.iloc[0]["precipitation_mm_per_day"]
                )

                if math.isclose(
                    nasa_municipal,
                    saved_value,
                    abs_tol=1e-6,
                ):

                    print(
                        f"  MUNICIPAL: PASS | "
                        f"NASA={nasa_municipal:.6f} | "
                        f"Saved={saved_value:.6f} mm/day"
                    )

                else:

                    failed += 1

                    print(
                        f"  MUNICIPAL: FAILED | "
                        f"NASA={nasa_municipal:.6f} | "
                        f"Saved={saved_value:.6f} mm/day"
                    )

            else:

                failed += 1

                print(
                    "  MUNICIPAL: FAILED | "
                    "Missing or duplicate saved record"
                )

    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    print("Successful grid observations:", passed)
    print("Failed comparisons:", failed)
    print("Expected grid observations:", len(TEST_DATES) * len(weights))

    if failed == 0 and passed == len(TEST_DATES) * len(weights):
        print("\nRESULT: ALL SOURCE COMPARISONS PASSED")
    else:
        print("\nRESULT: VERIFICATION FAILED")


if __name__ == "__main__":
    main()
