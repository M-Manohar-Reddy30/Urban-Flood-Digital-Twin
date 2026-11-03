from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[1]

ORIGINAL = ROOT / "data/processed/hydrology/conditioning/ballari_dem_whitebox_input.tif"
BREACHED = ROOT / "data/processed/hydrology/conditioning/ballari_dem_breached.tif"
BOUNDARY = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"
OUT = ROOT / "data/processed/hydrology/conditioning/breaching_change_locations.csv"

boundary = gpd.read_file(BOUNDARY).to_crs("EPSG:32643")
municipal = boundary.geometry.union_all()

with rasterio.open(ORIGINAL) as src, rasterio.open(BREACHED) as dst:
    before = src.read(1)
    after = dst.read(1)

    valid = (
        np.isfinite(before) & (before != src.nodata)
        & np.isfinite(after) & (after != dst.nodata)
    )

    delta = after - before
    changed = valid & (np.abs(delta) > 0.001)

    city_mask = geometry_mask(
        [mapping(municipal)],
        out_shape=before.shape,
        transform=src.transform,
        invert=True,
        all_touched=False,
    )

    rows, cols = np.where(changed)
    records = []

    for row, col in zip(rows, cols):
        x, y = rasterio.transform.xy(src.transform, row, col)
        point = __import__("shapely.geometry", fromlist=["Point"]).Point(x, y)
        change = float(delta[row, col])

        records.append({
            "row": int(row),
            "col": int(col),
            "easting_m": x,
            "northing_m": y,
            "original_elevation_m": float(before[row, col]),
            "conditioned_elevation_m": float(after[row, col]),
            "elevation_change_m": change,
            "change_type": "lowered" if change < 0 else "raised",
            "inside_municipal_boundary": bool(city_mask[row, col]),
            "distance_to_city_km": point.distance(municipal) / 1000,
        })

df = pd.DataFrame(records)
df["absolute_change_m"] = df["elevation_change_m"].abs()

df.sort_values(
    "absolute_change_m", ascending=False
).to_csv(OUT, index=False)

print("TOTAL CHANGED CELLS:", len(df))
print("SAVED:", OUT)

print("\nTOP 20 LARGEST CHANGES")
print(df.nlargest(20, "absolute_change_m")[
    ["easting_m", "northing_m", "original_elevation_m",
     "conditioned_elevation_m", "elevation_change_m",
     "inside_municipal_boundary", "distance_to_city_km"]
].to_string(index=False))

city = df[df["inside_municipal_boundary"]]

print("\nMUNICIPAL CHANGE SUMMARY")
print("Changed cells:", len(city))
print("Lowered:", int((city["elevation_change_m"] < 0).sum()))
print("Raised:", int((city["elevation_change_m"] > 0).sum()))
print("Largest municipal changes:")
print(city.nlargest(15, "absolute_change_m")[
    ["easting_m", "northing_m", "original_elevation_m",
     "conditioned_elevation_m", "elevation_change_m"]
].to_string(index=False))
