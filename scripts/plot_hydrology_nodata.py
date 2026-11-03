from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.plot import plotting_extent
from scipy.ndimage import label

ROOT = Path(__file__).resolve().parents[1]

DEM = ROOT / "data/processed/hydrology/ballari_hydrology_dem_30m.tif"
BOUNDARY = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"
OUTPUT = ROOT / "data/processed/hydrology/ballari_nodata_diagnostic.png"

with rasterio.open(DEM) as src:
    data = src.read(1)
    transform = src.transform
    nodata = src.nodata
    extent = plotting_extent(src)

valid = np.isfinite(data)
if nodata is not None:
    valid &= data != nodata

boundary = gpd.read_file(BOUNDARY).to_crs("EPSG:32643")
city = boundary.geometry.union_all()
buffered = city.buffer(10000)

inside = rasterize(
    [(buffered, 1)],
    out_shape=data.shape,
    transform=transform,
).astype(bool)

missing = inside & ~valid
labels, count = label(missing)

fig, axes = plt.subplots(1, 2, figsize=(16, 8))

axes[0].imshow(
    np.where(valid, data, np.nan),
    extent=extent,
    origin="upper",
    cmap="terrain",
)
gpd.GeoSeries([buffered], crs=boundary.crs).boundary.plot(
    ax=axes[0], color="blue", linewidth=0.8
)
boundary.boundary.plot(ax=axes[0], color="red", linewidth=1.4)
axes[0].set_title("Hydrology DEM and study boundaries")

axes[1].imshow(
    np.where(missing, labels, np.nan),
    extent=extent,
    origin="upper",
    interpolation="nearest",
    cmap="tab20",
)
gpd.GeoSeries([buffered], crs=boundary.crs).boundary.plot(
    ax=axes[1], color="blue", linewidth=0.8
)
boundary.boundary.plot(ax=axes[1], color="red", linewidth=1.4)
axes[1].set_title("NoData components inside 10 km buffer")

for component_id in [47, 181]:
    rows, cols = np.where(labels == component_id)
    if len(rows):
        print(
            f"Component {component_id}: "
            f"{len(rows)} pixels, "
            f"row range {rows.min()}–{rows.max()}, "
            f"column range {cols.min()}–{cols.max()}, "
            f"occupied rows {len(np.unique(rows))}, "
            f"occupied columns {len(np.unique(cols))}"
        )

for ax in axes:
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    ax.set_aspect("equal")

plt.tight_layout()
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUTPUT, dpi=180, bbox_inches="tight")
plt.close()

print("\nSaved:", OUTPUT)
