from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from scipy import ndimage
from shapely.geometry import Point
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]

ORIGINAL = ROOT / "data/processed/hydrology/conditioning/ballari_dem_whitebox_input.tif"
BREACHED = ROOT / "data/processed/hydrology/conditioning/ballari_dem_pure_breached.tif"
DRAINAGE = ROOT / "data/processed/drainage/ballari_drainage_clipped.geojson"
OUTPUT = ROOT / "data/processed/hydrology/conditioning/breaching_clusters.csv"

with rasterio.open(ORIGINAL) as src, rasterio.open(BREACHED) as dst:
    before = src.read(1)
    after = dst.read(1)
    transform = src.transform
    crs = src.crs
    nodata = src.nodata

valid = (
    np.isfinite(before) & (before != nodata)
    & np.isfinite(after) & (after != dst.nodata)
)

delta = after - before
changed = valid & (np.abs(delta) > 0.001)

# 8-connected clusters
labels, count = ndimage.label(
    changed,
    structure=np.ones((3, 3), dtype=np.uint8)
)

drainage = gpd.read_file(DRAINAGE).to_crs(crs)
drainage_union = unary_union(drainage.geometry)

records = []

for cluster_id in range(1, count + 1):
    rows, cols = np.where(labels == cluster_id)

    if len(rows) < 3:
        continue

    changes = delta[rows, cols]
    xs, ys = rasterio.transform.xy(transform, rows, cols)

    points = [Point(x, y) for x, y in zip(xs, ys)]
    cluster_geometry = unary_union(points)

    records.append({
        "cluster_id": cluster_id,
        "cells": len(rows),
        "area_km2": len(rows) * abs(transform.a * transform.e) / 1_000_000,
        "lowered_cells": int((changes < -0.001).sum()),
        "raised_cells": int((changes > 0.001).sum()),
        "minimum_change_m": float(changes.min()),
        "maximum_change_m": float(changes.max()),
        "mean_absolute_change_m": float(np.abs(changes).mean()),
        "drainage_distance_m": float(cluster_geometry.distance(drainage_union)),
        "centroid_easting": float(np.mean(xs)),
        "centroid_northing": float(np.mean(ys)),
    })

df = pd.DataFrame(records)

if not df.empty:
    df = df.sort_values("cells", ascending=False)
    df.to_csv(OUTPUT, index=False)

    print("Clusters:", len(df))
    print("Saved:", OUTPUT)
    print("\nLargest 20 clusters:")
    print(df.head(20).to_string(index=False))

    print("\nClusters with maximum lowering:")
    print(df.nsmallest(10, "minimum_change_m").to_string(index=False))
else:
    print("No clusters with at least 3 changed cells.")
