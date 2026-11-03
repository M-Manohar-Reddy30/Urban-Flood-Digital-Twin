from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import label
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]

DEM = ROOT / "data/processed/hydrology/ballari_hydrology_dem_30m.tif"
BOUNDARY = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"

with rasterio.open(DEM) as src:
    data = src.read(1)
    transform = src.transform
    nodata = src.nodata
    crs = src.crs
    height, width = data.shape

boundary = gpd.read_file(BOUNDARY).to_crs(crs)
city = boundary.geometry.union_all()
buffered = city.buffer(10000)

inside_buffer = rasterize(
    [(buffered, 1)],
    out_shape=data.shape,
    transform=transform,
).astype(bool)

valid = np.isfinite(data)
if nodata is not None:
    valid &= data != nodata

missing = inside_buffer & ~valid

labels, count = label(missing)

records = []

for component_id in range(1, count + 1):
    rows, cols = np.where(labels == component_id)

    if len(rows) == 0:
        continue

    row_min, row_max = rows.min(), rows.max()
    col_min, col_max = cols.min(), cols.max()

    left, top = rasterio.transform.xy(
        transform, row_min, col_min, offset="ul"
    )
    right, bottom = rasterio.transform.xy(
        transform, row_max, col_max, offset="lr"
    )

    geom = box(left, bottom, right, top)

    records.append({
        "component_id": component_id,
        "pixels": len(rows),
        "area_km2": len(rows) * abs(transform.a * transform.e) / 1e6,
        "distance_to_city_m": geom.distance(city),
        "centroid_easting": geom.centroid.x,
        "centroid_northing": geom.centroid.y,
        "bounds": geom.bounds,
    })

result = pd.DataFrame(records).sort_values(
    "pixels", ascending=False
)

print("LARGEST NODATA COMPONENTS")
print("=" * 65)

if result.empty:
    print("No missing components found.")
else:
    print(result.head(15).drop(columns="bounds").round(2).to_string(index=False))

    print("\nLargest component bounds:")
    for _, row in result.head(5).iterrows():
        print(
            f"Component {int(row.component_id)} | "
            f"{int(row.pixels)} pixels | "
            f"{row.bounds}"
        )

OUTPUT = ROOT / "data/processed/hydrology/nodata_components.csv"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
result.to_csv(OUTPUT, index=False)

print("\nSaved:", OUTPUT)
print("Original DEM unchanged.")
