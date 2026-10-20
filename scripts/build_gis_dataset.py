from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import xy
from rasterio.warp import transform

ROOT = Path(__file__).resolve().parents[1]

paths = {
    "elevation_m": ROOT / "data/processed/dem/ballari_dem_utm43_corrected.tif",
    "slope_degrees": ROOT / "data/processed/slope/ballari_slope_degrees_corrected.tif",
    "landcover_class": ROOT / "data/processed/ballari_landcover_utm43_aligned.tif",
}

output_path = ROOT / "data/processed/ballari_gis_features.csv"

with rasterio.open(paths["elevation_m"]) as elevation_src, \
     rasterio.open(paths["slope_degrees"]) as slope_src, \
     rasterio.open(paths["landcover_class"]) as landcover_src:

    assert elevation_src.crs == slope_src.crs == landcover_src.crs
    assert elevation_src.transform == slope_src.transform == landcover_src.transform
    assert elevation_src.width == slope_src.width == landcover_src.width
    assert elevation_src.height == slope_src.height == landcover_src.height

    elevation = elevation_src.read(1, masked=True)
    slope = slope_src.read(1, masked=True)
    landcover = landcover_src.read(1, masked=True)

    valid = (
        ~np.ma.getmaskarray(elevation)
        & ~np.ma.getmaskarray(slope)
        & ~np.ma.getmaskarray(landcover)
        & (landcover.filled(0) != 0)
    )

    rows, cols = np.where(valid)

    x, y = xy(elevation_src.transform, rows, cols, offset="center")

    lon, lat = transform(
        elevation_src.crs,
        "EPSG:4326",
        list(x),
        list(y),
    )

    df = pd.DataFrame({
        "longitude": lon,
        "latitude": lat,
        "easting_m": x,
        "northing_m": y,
        "elevation_m": elevation.data[rows, cols],
        "slope_degrees": slope.data[rows, cols],
        "landcover_class": landcover.data[rows, cols].astype(np.uint8),
    })

output_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(output_path, index=False)

print("Saved:", output_path)
print("Valid grid cells:", len(df))
print("Columns:", ", ".join(df.columns))
print("\nLand-cover class counts:")
print(df["landcover_class"].value_counts().sort_index().to_string())
print("\nFeature summary:")
print(df[["elevation_m", "slope_degrees"]].describe().round(2).to_string())
