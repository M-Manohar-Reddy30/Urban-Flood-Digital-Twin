from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import label

ROOT = Path(__file__).resolve().parents[1]

DEM = ROOT / "data/processed/hydrology/ballari_hydrology_dem_30m.tif"
BOUNDARY = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"

with rasterio.open(DEM) as src:
    dem = src.read(1)
    transform = src.transform
    nodata = src.nodata
    crs = src.crs

boundary = gpd.read_file(BOUNDARY).to_crs(crs)
city = boundary.geometry.union_all()
buffered = city.buffer(10000)

inside_buffer = rasterize(
    [(buffered, 1)],
    out_shape=dem.shape,
    transform=transform,
).astype(bool)

inside_city = rasterize(
    [(city, 1)],
    out_shape=dem.shape,
    transform=transform,
).astype(bool)

valid = np.isfinite(dem)
if nodata is not None:
    valid &= dem != nodata

def report(name, area):
    valid_area = area & valid
    missing_area = area & ~valid

    total = int(area.sum())
    good = int(valid_area.sum())
    missing = int(missing_area.sum())

    print(f"\n{name}")
    print("-" * 45)
    print("Total cells:", total)
    print("Valid cells:", good)
    print("Missing cells:", missing)
    print("Valid coverage (%):", round(good / total * 100, 4) if total else 0)

    if missing:
        components, count = label(missing_area)
        sizes = np.bincount(components.ravel())[1:]
        print("Missing components:", count)
        print("Largest missing components:", sorted(
            sizes.tolist(), reverse=True
        )[:10])

print("HYDROLOGY DEM QUALITY AUDIT")
print("=" * 55)

report("MUNICIPAL AREA", inside_city)
report("10 KM BUFFER AREA", inside_buffer)

print("\nRASTER EDGE")
print("Top edge valid:", int(valid[0, :].sum()), "/", dem.shape[1])
print("Bottom edge valid:", int(valid[-1, :].sum()), "/", dem.shape[1])
print("Left edge valid:", int(valid[:, 0].sum()), "/", dem.shape[0])
print("Right edge valid:", int(valid[:, -1].sum()), "/", dem.shape[0])

print("\nDEM CRS:", crs)
print("DEM dimensions:", dem.shape)
print("Original source remains unchanged.")
