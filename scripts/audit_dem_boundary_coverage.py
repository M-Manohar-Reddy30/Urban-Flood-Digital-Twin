from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import label

ROOT = Path(__file__).resolve().parents[1]

DEM = ROOT / "data/processed/dem/ballari_dem_utm43_corrected.tif"
BOUNDARY = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"

with rasterio.open(DEM) as src:
    elevation = src.read(1)
    transform = src.transform
    crs = src.crs
    nodata = src.nodata
    shape = elevation.shape
    pixel_area = abs(transform.a * transform.e)

boundary = gpd.read_file(BOUNDARY)

if boundary.crs is None:
    raise ValueError("Boundary CRS is missing.")

boundary = boundary.to_crs(crs)
geometries = [
    geom for geom in boundary.geometry
    if geom is not None and not geom.is_empty
]

inside = rasterize(
    [(geom, 1) for geom in geometries],
    out_shape=shape,
    transform=transform,
    fill=0,
    dtype="uint8",
).astype(bool)

valid = np.isfinite(elevation)

if nodata is not None:
    valid &= elevation != nodata

valid_inside = inside & valid
missing_inside = inside & ~valid

total = int(inside.sum())
valid_count = int(valid_inside.sum())
missing_count = int(missing_inside.sum())

print("DEM COVERAGE INSIDE MUNICIPAL BOUNDARY")
print("=" * 55)
print("Municipal raster cells:", total)
print("Valid DEM cells:", valid_count)
print("Missing DEM cells:", missing_count)

coverage = valid_count / total * 100 if total else 0
print("Valid coverage:", round(coverage, 4), "%")

print("Rasterized municipal area:", round(total * pixel_area / 1e6, 4), "km²")
print("Valid DEM area:", round(valid_count * pixel_area / 1e6, 4), "km²")
print("Missing area:", round(missing_count * pixel_area / 1e6, 4), "km²")

if missing_count:
    components, count = label(missing_inside)
    sizes = np.bincount(components.ravel())[1:]

    print("\nMISSING-DATA COMPONENTS")
    print("Connected missing regions:", count)
    print("Largest missing components (pixels):", sorted(
        sizes.tolist(), reverse=True
    )[:10])
else:
    print("\nNo missing DEM pixels detected inside the rasterized boundary.")

print("\nOriginal DEM remains unchanged.")
