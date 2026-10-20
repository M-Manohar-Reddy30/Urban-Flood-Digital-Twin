from pathlib import Path

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
source = (
    ROOT
    / "data/raw/rainfall/nasa_imerg/"
    / "3B-DAY.MS.MRG.3IMERG.20241231-S000000-E235959.V07B.nc4"
)

# Approximate centre of the Ballari municipal area
target_lat = 15.13
target_lon = 76.92

with h5py.File(source, "r") as f:
    lat = f["lat"][:]
    lon = f["lon"][:]
    rainfall = f["precipitation"][0, :, :]

    lat_idx = int(np.abs(lat - target_lat).argmin())
    lon_idx = int(np.abs(lon - target_lon).argmin())

    value = float(rainfall[lon_idx, lat_idx])

    print("Source file:", source.name)
    print("Date: 2024-12-31")
    print("Target coordinates:", target_lat, target_lon)
    print("Grid-cell centre:", float(lat[lat_idx]), float(lon[lon_idx]))
    print("Precipitation estimate (mm/day):", value)
    print("Variable units:", f["precipitation"].attrs.get("units"))
