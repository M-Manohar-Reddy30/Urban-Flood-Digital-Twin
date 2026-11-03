from pathlib import Path
import rasterio
import numpy as np
from whitebox import WhiteboxTools

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "data/processed/hydrology/ballari_hydrology_dem_30m_complete.tif"
OUTPUT_DIR = ROOT / "data/processed/hydrology/conditioning"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BREACHED = OUTPUT_DIR / "ballari_dem_breached.tif"
FILLED = OUTPUT_DIR / "ballari_dem_filled.tif"

wbt = WhiteboxTools()
wbt.set_working_dir(str(OUTPUT_DIR))
wbt.set_verbose_mode(True)

if not INPUT.exists():
    raise FileNotFoundError(INPUT)

print("\nEXPERIMENT 1: LEAST-COST BREACHING")

result = wbt.breach_depressions_least_cost(
    dem=str(INPUT),
    output=str(BREACHED),
    dist=100,
    min_dist=True
)

if result != 0 or not BREACHED.exists():
    raise RuntimeError("Depression breaching failed.")

print("\nEXPERIMENT 2: DEPRESSION FILLING")

result = wbt.fill_depressions(
    dem=str(INPUT),
    output=str(FILLED),
    fix_flats=True
)

if result != 0 or not FILLED.exists():
    raise RuntimeError("Depression filling failed.")

print("\nEXPERIMENT 3: ELEVATION CHANGE COMPARISON")

with rasterio.open(INPUT) as original, \
     rasterio.open(BREACHED) as breached, \
     rasterio.open(FILLED) as filled:

    original_data = original.read(1)
    breached_data = breached.read(1)
    filled_data = filled.read(1)

    valid = (
        np.isfinite(original_data)
        & (original_data != original.nodata)
        & np.isfinite(breached_data)
        & (breached_data != breached.nodata)
        & np.isfinite(filled_data)
        & (filled_data != filled.nodata)
    )

    if not (
        original.crs == breached.crs == filled.crs
        and original.transform == breached.transform == filled.transform
        and original.width == breached.width == filled.width
        and original.height == breached.height == filled.height
    ):
        raise ValueError("Output raster alignment mismatch.")

    for name, result_data in [
        ("BREACHING", breached_data),
        ("FILLING", filled_data)
    ]:
        change = result_data[valid] - original_data[valid]
        changed = np.abs(change) > 0.001

        print(f"\n{name}")
        print("Changed cells:", int(changed.sum()))
        print("Percentage changed:", round(changed.mean() * 100, 4))
        print("Minimum elevation change:", round(float(change.min()), 3), "m")
        print("Maximum elevation change:", round(float(change.max()), 3), "m")
        print("Mean absolute change:", round(float(np.abs(change).mean()), 3), "m")
        print("RMSE:", round(float(np.sqrt(np.mean(change ** 2))), 3), "m")

print("\nBoth conditioning experiments completed.")
print("Original DEM was not modified.")
