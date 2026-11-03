from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio

from rasterio.features import shapes
from rasterio.windows import Window
from shapely.geometry import shape
from shapely.ops import unary_union
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]

BASE = ROOT / "data/processed/hydrology/conditioning"

ORIGINAL = BASE / "ballari_dem_whitebox_input.tif"
BREACHED = BASE / "ballari_dem_pure_breached.tif"
DRAINAGE = ROOT / "data/processed/drainage/ballari_drainage_clipped.geojson"

OUT = BASE / "hotspot_inspection"
OUT.mkdir(parents=True, exist_ok=True)

with rasterio.open(ORIGINAL) as src:
    before = src.read(1)
    before_valid = src.read_masks(1) > 0
    profile = src.profile.copy()
    transform = src.transform
    crs = src.crs

    with rasterio.open(BREACHED) as dst:
        after = dst.read(1)
        after_valid = dst.read_masks(1) > 0

        assert src.shape == dst.shape
        assert src.transform == dst.transform
        assert src.crs == dst.crs

valid = (
    before_valid
    & after_valid
    & np.isfinite(before)
    & np.isfinite(after)
)

delta = after - before
hotspots = valid & (delta < -5)

labels, count = ndimage.label(
    hotspots,
    structure=np.ones((3, 3), dtype=np.uint8)
)

drainage = gpd.read_file(DRAINAGE).to_crs(crs)
drainage_union = unary_union(
    drainage.geometry.dropna().tolist()
)

# Previously identified severe clusters
selected = [15, 17, 11]

records = []

for cluster_id in selected:

    mask = labels == cluster_id
    rows, cols = np.where(mask)

    if len(rows) == 0:
        print("Cluster not found:", cluster_id)
        continue

    geometries = [
        shape(geom)
        for geom, value in shapes(
            labels.astype(np.int32),
            mask=mask,
            transform=transform
        )
        if int(value) == cluster_id
    ]

    hotspot_geometry = unary_union(geometries)

    min_distance = hotspot_geometry.distance(drainage_union)

    # Extract a local DEM window with 20-cell buffer
    buffer = 20

    r0 = max(0, int(rows.min()) - buffer)
    r1 = min(before.shape[0], int(rows.max()) + buffer + 1)

    c0 = max(0, int(cols.min()) - buffer)
    c1 = min(before.shape[1], int(cols.max()) + buffer + 1)

    window = Window(
        c0, r0, c1 - c0, r1 - r0
    )

    original_patch = before[r0:r1, c0:c1].copy()
    breached_patch = after[r0:r1, c0:c1].copy()
    delta_patch = delta[r0:r1, c0:c1].copy()

    patch_valid = valid[r0:r1, c0:c1]

    patch_profile = profile.copy()
    patch_profile.update({
        "height": original_patch.shape[0],
        "width": original_patch.shape[1],
        "transform": rasterio.windows.transform(
            window, transform
        ),
        "count": 3,
        "dtype": "float32",
        "nodata": -9999.0,
        "compress": "deflate"
    })

    output_file = OUT / f"cluster_{cluster_id}_inspection.tif"

    with rasterio.open(
        output_file, "w", **patch_profile
    ) as dst:

        for band, array in enumerate(
            [original_patch, breached_patch, delta_patch],
            start=1
        ):
            output = array.astype(np.float32).copy()
            output[~patch_valid] = -9999.0

            dst.write(output, band)

        dst.set_band_description(1, "Original DEM")
        dst.set_band_description(2, "Breached DEM")
        dst.set_band_description(3, "Elevation Difference")

    records.append({
        "cluster_id": cluster_id,
        "cells": len(rows),
        "minimum_change_m": float(delta[mask].min()),
        "polygon_drainage_distance_m": float(min_distance),
        "inspection_file": str(output_file)
    })

report = pd.DataFrame(records)

report.to_csv(
    OUT / "inspection_summary.csv",
    index=False
)

print("\n========== HOTSPOT INSPECTION ==========")
print(report.to_string(index=False))

print("\nInspection files saved to:", OUT)
