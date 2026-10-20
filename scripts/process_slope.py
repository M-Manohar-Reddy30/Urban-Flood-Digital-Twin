
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import sobel, binary_erosion

ROOT = Path(__file__).resolve().parents[1]
dem_path = ROOT / "data/processed/dem/ballari_dem_utm43_corrected.tif"
out_path = ROOT / "data/processed/slope/ballari_slope_degrees_corrected.tif"

with rasterio.open(dem_path) as src:
    dem = src.read(1, masked=True)
    profile = src.profile.copy()
    transform = src.transform

    valid = ~np.ma.getmaskarray(dem)
    elevation = dem.filled(0).astype("float64")

    # Require a complete 3x3 neighborhood to avoid NoData-edge artefacts.
    safe = binary_erosion(
        valid,
        structure=np.ones((3, 3), dtype=bool),
        border_value=0,
    )

    dz_dx = sobel(elevation, axis=1, mode="nearest") / (
        8.0 * transform.a
    )
    dz_dy = sobel(elevation, axis=0, mode="nearest") / (
        8.0 * abs(transform.e)
    )

    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))
    slope[~safe] = -9999.0

    profile.update(
        dtype="float32",
        count=1,
        nodata=-9999.0,
        compress="deflate",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(slope.astype("float32"), 1)

with rasterio.open(out_path) as src:
    values = src.read(1, masked=True).compressed()
    print("Saved:", out_path)
    print("Valid slope pixels:", values.size)
    print("Minimum slope (degrees):", round(float(values.min()), 2))
    print("Maximum slope (degrees):", round(float(values.max()), 2))
    print("Mean slope (degrees):", round(float(values.mean()), 2))
    print("Pixels above 45 degrees:", int(np.count_nonzero(values > 45)))
