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

TEST_DATES = [
    date(2001, 1, 1),
    date(2010, 8, 19),
    date(2024, 12, 31),
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

    lat = float(matches["lat"].group(1))
    lon = float(matches["lon"].group(1))
    rainfall = float(matches["rain"].group(1))
    count = float(matches["count"].group(1))

    if not math.isclose(lat, float(cell["latitude"]), abs_tol=0.001):
        raise ValueError("Latitude mismatch")

    if not math.isclose(lon, float(cell["longitude"]), abs_tol=0.001):
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

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    weights = pd.read_csv(WEIGHTS_FILE)

    print("FOUR-CELL HISTORICAL VERIFICATION")
    print("=" * 65)

    passed = 0
    failed = 0

    for day in TEST_DATES:
        print(f"\nDate: {day}")

        for _, cell in weights.iterrows():
            try:
                rainfall, count = fetch_and_validate_observation(day, cell, token)
                passed += 1

                print(
                    f"  {cell['grid_id']}: PASS | "
                    f"{rainfall} mm/day | {count} retrievals"
                )

            except Exception as exc:
                failed += 1
                print(
                    f"  {cell['grid_id']}: FAILED | "
                    f"{type(exc).__name__}: {exc}"
                )

    print("\n" + "=" * 65)
    print("Successful observations:", passed)
    print("Failed observations:", failed)
    print("Expected observations:", len(TEST_DATES) * len(weights))


if __name__ == "__main__":
    main()