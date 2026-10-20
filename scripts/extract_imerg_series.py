from pathlib import Path

import h5py
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
input_dir = ROOT / "data/raw/rainfall/nasa_imerg"
output_path = ROOT / "data/processed/rainfall/nasa_imerg_ballari_2024.csv"

target_lat = 15.13
target_lon = 76.92
records = []

for path in sorted(input_dir.glob("*.nc4")):
    try:
        with h5py.File(path, "r") as f:
            lat = f["lat"][:]
            lon = f["lon"][:]

            lat_idx = int(np.abs(lat - target_lat).argmin())
            lon_idx = int(np.abs(lon - target_lon).argmin())

            value = float(f["precipitation"][0, lon_idx, lat_idx])
            count = float(f["precipitation_cnt"][0, lon_idx, lat_idx])
            fill_value = float(np.asarray(
                f["precipitation"].attrs["_FillValue"]
            ).reshape(-1)[0])

            date_text = path.name.split(".3IMERG.")[1][:8]
            date = pd.to_datetime(date_text, format="%Y%m%d")

            valid = (
                np.isfinite(value)
                and value != fill_value
                and value >= 0
                and np.isfinite(count)
                and count > 0
            )

            records.append({
                "date": date,
                "latitude": float(lat[lat_idx]),
                "longitude": float(lon[lon_idx]),
                "precipitation_mm_per_day": value if valid else np.nan,
                "valid_half_hourly_retrievals": count,
                "quality_status": "valid" if valid else "missing_or_invalid",
                "source_file": path.name,
            })

    except Exception as exc:
        print(f"Could not process {path.name}: {exc}")

output_path.parent.mkdir(parents=True, exist_ok=True)
df = pd.DataFrame(records).sort_values("date")
df.to_csv(output_path, index=False)

print("Saved:", output_path)
print("Files processed:", len(df))
print("Valid observations:", int(df["precipitation_mm_per_day"].notna().sum()))
print("Invalid/missing observations:", int(df["precipitation_mm_per_day"].isna().sum()))
print(df[["date", "precipitation_mm_per_day",
          "valid_half_hourly_retrievals", "quality_status"]].to_string(index=False))
