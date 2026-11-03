from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.plot import plotting_extent

ROOT = Path(__file__).resolve().parents[1]

DEM = ROOT / "data/processed/dem/ballari_dem_utm43_corrected.tif"
BOUNDARY = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"

OUTPUT = ROOT / "data/processed/dem/ballari_dem_coverage_diagnostic.png"

with rasterio.open(DEM) as src:
    elevation = src.read(1).astype("float32")
    valid = np.isfinite(elevation) & (elevation != src.nodata)
    extent = plotting_extent(src)

boundary = gpd.read_file(BOUNDARY)

if boundary.crs is None:
    raise ValueError("Municipal boundary CRS is missing.")

boundary = boundary.to_crs("EPSG:32643")

fig, axes = plt.subplots(1, 2, figsize=(15, 7))

axes[0].imshow(
    np.where(valid, elevation, np.nan),
    extent=extent,
    origin="upper",
    cmap="terrain",
)
boundary.boundary.plot(ax=axes[0], color="red", linewidth=1.2)
axes[0].set_title("DEM elevation and municipal boundary")
axes[0].set_xlabel("Easting (m)")
axes[0].set_ylabel("Northing (m)")

axes[1].imshow(
    valid.astype("uint8"),
    extent=extent,
    origin="upper",
    cmap="gray",
    vmin=0,
    vmax=1,
)
boundary.boundary.plot(ax=axes[1], color="red", linewidth=1.2)
axes[1].set_title("DEM valid-data coverage")
axes[1].set_xlabel("Easting (m)")
axes[1].set_ylabel("Northing (m)")

plt.tight_layout()
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUTPUT, dpi=180, bbox_inches="tight")
plt.close()

print("Saved:", OUTPUT)
print("Valid coverage:", round(valid.mean() * 100, 2), "%")
print("Boundary CRS:", boundary.crs)
print("Boundary count:", len(boundary))
