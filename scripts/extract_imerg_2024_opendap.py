
import csv
import math
import re
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

# NASA GPM IMERG Final Daily Precipitation V07
BASE_URL = (
    "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/hyrax/"
    "GPM_L3/GPM_3IMERGDF.07"
)

# Verified NASA grid cell near Ballari
LATITUDE = 15.15
LONGITUDE = 76.95

# Array dimensions: time, longitude, latitude
LON_INDEX = 2569
LAT_INDEX = 1051

START_DATE = date(2024, 1, 1)
END_DATE = date(2024, 12, 31)

TOKEN_FILE = Path.home() / ".earthdata_token"
OUTPUT_FILE = Path(
    "data/processed/rainfall/nasa_imerg_ballari_2024.csv"
)


def fetch_daily_observation(day, token):
    """Fetch one grid cell's daily precipitation and retrieval count."""

    filename = (
        f"3B-DAY.MS.MRG.3IMERG.{day:%Y%m%d}"
        "-S000000-E235959.V07B.nc4"
    )

    constraint = (
        f"precipitation[0:1:0]"
        f"[{LON_INDEX}:1:{LON_INDEX}]"
        f"[{LAT_INDEX}:1:{LAT_INDEX}],"
        f"precipitation_cnt[0:1:0]"
        f"[{LON_INDEX}:1:{LON_INDEX}]"
        f"[{LAT_INDEX}:1:{LAT_INDEX}]"
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

    if "Dataset:" not in body:
        raise ValueError(f"Unexpected NASA response: {body[:200]}")

    # NASA returns lines such as:
    # precipitation.lat, 15.15
    # precipitation.precipitation[...], 0
    # precipitation_cnt.lat, 15.15
    # precipitation_cnt.precipitation_cnt[...], 48

    latitude_match = re.search(
        r"(?m)^precipitation\.lat,\s*([-+0-9.eE]+)\s*$",
        body,
    )

    longitude_match = re.search(
        r"(?m)^precipitation\.precipitation"
        r"\[.*?\.lon=([-+0-9.eE]+)\],\s*"
        r"([-+0-9.eE]+|NaN)\s*$",
        body,
    )

    precipitation_match = re.search(
        r"(?m)^precipitation\.precipitation"
        r"\[.*?\],\s*([-+0-9.eE]+|NaN)\s*$",
        body,
    )

    count_match = re.search(
        r"(?m)^precipitation_cnt\.precipitation_cnt"
        r"\[.*?\],\s*([-+0-9.eE]+|NaN)\s*$",
        body,
    )

    if not all(
        [
            latitude_match,
            longitude_match,
            precipitation_match,
            count_match,
        ]
    ):
        raise ValueError(
            "Could not parse NASA CSV response: " + body[:300]
        )

    actual_latitude = float(latitude_match.group(1))
    actual_longitude = float(longitude_match.group(1))
    precipitation_text = precipitation_match.group(1)
    count_text = count_match.group(1)

    if not math.isclose(actual_latitude, LATITUDE, abs_tol=0.001):
        raise ValueError(f"Unexpected latitude: {actual_latitude}")

    if not math.isclose(actual_longitude, LONGITUDE, abs_tol=0.001):
        raise ValueError(f"Unexpected longitude: {actual_longitude}")

    precipitation = float(precipitation_text)
    count_value = float(count_text)

    # NASA's fill value is -9999.9. Do not convert missing values to zero.
    if (
        not math.isfinite(precipitation)
        or not math.isfinite(count_value)
        or precipitation < 0
        or count_value < 0
        or math.isclose(precipitation, -9999.9)
        or math.isclose(count_value, -9999.9)
    ):
        return "", "", "missing_or_invalid"

    if count_value == 0:
        return precipitation, int(count_value), "no_valid_retrievals"

    return precipitation, int(count_value), "ok"


def main():
    if not TOKEN_FILE.is_file():
        raise SystemExit(
            f"Earthdata token file not found: {TOKEN_FILE}"
        )

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()

    if not token:
        raise SystemExit("Earthdata token file is empty.")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "date",
        "latitude",
        "longitude",
        "precipitation_mm_per_day",
        "valid_half_hourly_retrievals",
        "status",
    ]

    total_days = (END_DATE - START_DATE).days + 1
    successful = 0
    failed = 0
    missing = 0

    with OUTPUT_FILE.open(
        "w", newline="", encoding="utf-8"
    ) as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        current_day = START_DATE

        while current_day <= END_DATE:
            precipitation = ""
            count = ""
            status = "error"

            # Retry transient HTTP/network/parser errors.
            for attempt in range(3):
                try:
                    precipitation, count, status = (
                        fetch_daily_observation(current_day, token)
                    )
                    break
                except (
                    urllib.error.URLError,
                    TimeoutError,
                    ValueError,
                    OSError,
                ) as exc:
                    status = (
                        f"error: {type(exc).__name__}: {exc}"
                    )

                    if attempt < 2:
                        time.sleep(2 * (attempt + 1))

            if status == "ok":
                successful += 1
            elif status in ("missing_or_invalid", "no_valid_retrievals"):
                missing += 1
            else:
                failed += 1
                print(f"[FAILED] {current_day}: {status}")

            writer.writerow(
                {
                    "date": current_day.isoformat(),
                    "latitude": LATITUDE,
                    "longitude": LONGITUDE,
                    "precipitation_mm_per_day": precipitation,
                    "valid_half_hourly_retrievals": count,
                    "status": status,
                }
            )

            # Save progress after each daily request.
            output.flush()

            processed = (current_day - START_DATE).days + 1

            if processed % 10 == 0 or current_day == END_DATE:
                print(
                    f"{processed}/{total_days} days | "
                    f"valid={successful} | "
                    f"missing={missing} | failed={failed}"
                )

            current_day += timedelta(days=1)
            time.sleep(0.15)

    print("\nExtraction finished.")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Total expected days: {total_days}")
    print(f"Valid observations: {successful}")
    print(f"Missing/invalid observations: {missing}")
    print(f"Failed requests: {failed}")


if __name__ == "__main__":
    main()
