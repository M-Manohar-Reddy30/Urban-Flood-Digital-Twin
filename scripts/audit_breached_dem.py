from pathlib import Path
import numpy as np
import rasterio
import geopandas as gpd
from rasterio.features import geometry_mask
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[1]

ORIGINAL = ROOT / "data/processed/hydrology/conditioning/ballari_dem_whitebox_input.tif"
BREACHED = ROOT / "data/processed/hydrology/conditioning/ballari_dem_breached.tif"
BOUNDARY = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"

with rasterio.open(ORIGINAL) as src, rasterio.open(BREACHED) as dst:
    if not (
        src.crs == dst.crs
        and src.transform == dst.transform
        and src.width == dst.width
        and src.height == dst.height
    ):
        raise ValueError("Raster alignment mismatch.")

    original = src.read(1)
    conditioned = dst.read(1)

    original_valid = np.isfinite(original) & (original != src.nodata)
    conditioned_valid = np.isfinite(conditioned) & (conditioned != dst.nodata)

    common = original_valid & conditioned_valid

    if not common.any():
        raise ValueError("No overlapping valid elevation cells.")

    delta = conditioned[common] - original[common]
    changed = np.abs(delta) > 0.001

    print("BREACHED DEM AUDIT")
    print("=" * 55)
    print("CRS:", dst.crs)
    print("Dimensions:", dst.width, "x", dst.height)
    print("Resolution:", dst.res)
    print("Output NoData:", dst.nodata)
    print("Original valid cells:", int(original_valid.sum()))
    print("Conditioned valid cells:", int(conditioned_valid.sum()))
    print("Common valid cells:", int(common.sum()))
    print("Original-only valid cells:", int((original_valid & ~conditioned_valid).sum()))
    print("Conditioned-only valid cells:", int((conditioned_valid & ~original_valid).sum()))

    print("\nELEVATION CHANGES")
    print("-" * 55)
    print("Changed cells:", int(changed.sum()))
    print("Percentage changed:", round(float(changed.mean() * 100), 4))
    print("Lowered cells:", int((delta < -0.001).sum()))
    print("Raised cells:", int((delta > 0.001).sum()))
    print("Unchanged cells:", int((~changed).sum()))
    print("Minimum change:", round(float(delta.min()), 4), "m")
    print("Maximum change:", round(float(delta.max()), 4), "m")
    print("Mean absolute change:", round(float(np.abs(delta).mean()), 4), "m")
    print("RMSE:", round(float(np.sqrt(np.mean(delta ** 2))), 4), "m")
    print("95th percentile absolute change:",
          round(float(np.percentile(np.abs(delta), 95)), 4), "m")

    boundary = gpd.read_file(BOUNDARY).to_crs(dst.crs)
    municipal = boundary.geometry.union_all()

    municipal_mask = geometry_mask(
        [mapping(municipal)],
        out_shape=(dst.height, dst.width),
        transform=dst.transform,
        invert=True,
        all_touched=False,
    )

    city_common = municipal_mask & common
    city_delta = conditioned[city_common] - original[city_common]

    print("\nMUNICIPAL BOUNDARY")
    print("-" * 55)
    print("Valid comparison cells:", int(city_common.sum()))
    print("Changed cells:", int((np.abs(city_delta) > 0.001).sum()))
    print("Maximum absolute change:",
          round(float(np.abs(city_delta).max()), 4), "m")
    print("Mean absolute change:",
          round(float(np.abs(city_delta).mean()), 4), "m")

print("\nAudit completed. Neither input raster was modified.")
