from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import Point, mapping

ROOT = Path(__file__).resolve().parents[1]

DEM_FILE = ROOT / "data/processed/hydrology/ballari_hydrology_dem_30m_complete.tif"
BOUNDARY_FILE = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"
OUTPUT = ROOT / "data/processed/hydrology/remaining_dem_gap_locations.csv"

boundary = gpd.read_file(BOUNDARY_FILE).to_crs("EPSG:32643")
municipal = boundary.geometry.union_all()
buffered = municipal.buffer(10000)

records = []

with rasterio.open(DEM_FILE) as src:
    data = src.read(1)
    valid = np.isfinite(data) & (data != src.nodata)

    inside = geometry_mask(
        [mapping(buffered)],
        out_shape=data.shape,
        transform=src.transform,
        invert=True,
        all_touched=False,
    )

    missing_rows, missing_cols = np.where(inside & ~valid)

    for row, col in zip(missing_rows, missing_cols):
        x, y = rasterio.transform.xy(src.transform, row, col)
        point = Point(x, y)

        records.append({
            "row": int(row),
            "col": int(col),
            "easting": x,
            "northing": y,
            "longitude": point.x,
            "latitude": point.y,
            "distance_to_municipal_km": point.distance(municipal) / 1000,
            "distance_to_buffer_edge_m": point.distance(buffered.boundary),
            "near_raster_edge": (
                row < 10 or row >= src.height - 10
                or col < 10 or col >= src.width - 10
            ),
        })

df = pd.DataFrame(records)
df.to_csv(OUTPUT, index=False)

print("Missing pixels inspected:", len(df))
print("Saved:", OUTPUT)

if not df.empty:
    print("\nDistance from municipal boundary (km):")
    print(df["distance_to_municipal_km"].describe().round(3))

    print("\nDistance from buffer boundary (m):")
    print(df["distance_to_buffer_edge_m"].describe().round(2))

    print("\nNear raster edge:", int(df["near_raster_edge"].sum()))
    print("Away from raster edge:", int((~df["near_raster_edge"]).sum()))

    print("\nMissing pixels by raster edge:")
    print("Left:", int((df["col"] < 10).sum()))
    print("Right:", int((df["col"] >= 1156).sum()))
    print("Top:", int((df["row"] < 10).sum()))
    print("Bottom:", int((df["row"] >= 1075).sum()))

    print("\nFirst 15 locations:")
    print(df.head(15).to_string(index=False))
else:
    print("No missing pixels inside the buffer.")
