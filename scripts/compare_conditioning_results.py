from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processed/hydrology/conditioning"

ORIGINAL = BASE / "ballari_dem_whitebox_input.tif"

EXPERIMENTS = {
    "PURE_BREACH": BASE / "ballari_dem_pure_breached.tif",
    "BREACH_PLUS_FILL": BASE / "ballari_dem_breached.tif",
}

BOUNDARY = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"

boundary = gpd.read_file(BOUNDARY)

with rasterio.open(ORIGINAL) as src:
    original = src.read(1)
    profile = src.profile.copy()

    valid_original = (
        np.isfinite(original) & (original != src.nodata)
    )

    municipal = boundary.to_crs(src.crs).geometry.union_all()

    city_mask = geometry_mask(
        [mapping(municipal)],
        out_shape=original.shape,
        transform=src.transform,
        invert=True,
        all_touched=False,
    )

print("CONDITIONING COMPARISON")
print("=" * 65)

for name, path in EXPERIMENTS.items():
    if not path.exists():
        raise FileNotFoundError(path)

    with rasterio.open(path) as dst:
        if not (
            dst.crs == profile["crs"]
            and dst.transform == profile["transform"]
            and dst.width == profile["width"]
            and dst.height == profile["height"]
        ):
            raise ValueError(f"{name}: Raster alignment mismatch")

        result = dst.read(1)
        valid_result = np.isfinite(result) & (result != dst.nodata)

    common = valid_original & valid_result
    delta = result[common] - original[common]
    changed = np.abs(delta) > 0.001

    city_common = common & city_mask
    city_delta = result[city_common] - original[city_common]
    city_changed = np.abs(city_delta) > 0.001

    print(f"\n{name}")
    print("-" * 65)
    print("Valid output cells:", int(valid_result.sum()))
    print("Common valid cells:", int(common.sum()))
    print("Changed cells:", int(changed.sum()))
    print("Changed percentage:", round(float(changed.mean() * 100), 4))
    print("Lowered cells:", int((delta < -0.001).sum()))
    print("Raised cells:", int((delta > 0.001).sum()))
    print("Maximum lowering:", round(float(delta.min()), 3), "m")
    print("Maximum raising:", round(float(delta.max()), 3), "m")
    print("Mean absolute change:", round(float(np.abs(delta).mean()), 4), "m")
    print("RMSE:", round(float(np.sqrt(np.mean(delta ** 2))), 4), "m")

    print("\nMUNICIPAL AREA")
    print("Valid cells:", int(city_common.sum()))
    print("Changed cells:", int(city_changed.sum()))
    print("Changed percentage:", round(float(city_changed.mean() * 100), 4))
    print("Maximum absolute change:",
          round(float(np.abs(city_delta).max()), 3), "m")
    print("Mean absolute change:",
          round(float(np.abs(city_delta).mean()), 4), "m")

print("\nComparison completed. No input rasters were modified.")
