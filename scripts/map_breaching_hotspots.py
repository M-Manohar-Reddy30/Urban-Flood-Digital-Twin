from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio

from scipy import ndimage
from rasterio.features import shapes
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]

ORIGINAL = ROOT / "data/processed/hydrology/conditioning/ballari_dem_whitebox_input.tif"
BREACHED = ROOT / "data/processed/hydrology/conditioning/ballari_dem_pure_breached.tif"
DRAINAGE = ROOT / "data/processed/drainage/ballari_drainage_clipped.geojson"

OUT = ROOT / "data/processed/hydrology/conditioning"

with rasterio.open(ORIGINAL) as src:
    before = src.read(1)
    before_valid = src.read_masks(1) > 0
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

# Identify cells lowered by more than 5 metres
hotspots = valid & (delta < -5)

labels, count = ndimage.label(
    hotspots,
    structure=np.ones((3, 3), dtype=np.uint8)
)

drainage = gpd.read_file(DRAINAGE).to_crs(crs)

drainage_union = unary_union(
    drainage.geometry.dropna().tolist()
)

records = []
features = []

for cluster_id in range(1, count + 1):

    mask = labels == cluster_id
    rows, cols = np.where(mask)

    changes = delta[mask]

    xs, ys = rasterio.transform.xy(
        transform, rows, cols
    )

    centroid_x = float(np.mean(xs))
    centroid_y = float(np.mean(ys))

    from shapely.geometry import Point

    centroid = Point(centroid_x, centroid_y)

    distance = centroid.distance(drainage_union)

    records.append({
        "cluster_id": cluster_id,
        "cells": len(rows),
        "area_km2": len(rows) * abs(
            transform.a * transform.e
        ) / 1_000_000,
        "minimum_change_m": float(changes.min()),
        "mean_change_m": float(changes.mean()),
        "maximum_change_m": float(changes.max()),
        "drainage_distance_m": float(distance),
        "centroid_easting": centroid_x,
        "centroid_northing": centroid_y
    })

    for geom, value in shapes(
        labels.astype(np.int32),
        mask=mask,
        transform=transform
    ):
        if int(value) == cluster_id:
            features.append({
                "cluster_id": cluster_id,
                "cells": len(rows),
                "minimum_change_m": float(changes.min()),
                "geometry": shape(geom)
            })

df = pd.DataFrame(records)

if not df.empty:
    df = df.sort_values(
        "minimum_change_m"
    )

    df.to_csv(
        OUT / "breaching_hotspot_clusters.csv",
        index=False
    )

    hotspot_gdf = gpd.GeoDataFrame(
        features,
        geometry="geometry",
        crs=crs
    )

    hotspot_gdf.to_file(
        OUT / "breaching_hotspots.geojson",
        driver="GeoJSON"
    )

    print("\nHOTSPOT CLUSTERS:", len(df))

    print("\nHOTSPOT SUMMARY:")
    print(df.to_string(index=False))

    print("\nSaved CSV and GeoJSON hotspot files.")

else:
    print("No hotspots found.")
