from pathlib import Path
import numpy as np
import pandas as pd
import rasterio

ROOT = Path(__file__).resolve().parents[1]

ORIGINAL = ROOT / "data/processed/hydrology/conditioning/ballari_dem_whitebox_input.tif"
BREACHED = ROOT / "data/processed/hydrology/conditioning/ballari_dem_pure_breached.tif"

OUTPUT = ROOT / "data/processed/hydrology/conditioning/breaching_quality_report.csv"

with rasterio.open(ORIGINAL) as src:
    before = src.read(1)
    before_valid = src.read_masks(1) > 0

    transform = src.transform

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

changed = valid & (np.abs(delta) > 0.001)

lowered = changed & (delta < -0.001)
raised = changed & (delta > 0.001)

print("\n========== BREACHING QUALITY REPORT ==========")

print("Changed cells:", int(changed.sum()))
print("Lowered cells:", int(lowered.sum()))
print("Raised cells:", int(raised.sum()))

print("\nElevation modification statistics:")

print("Mean change among changed cells:",
      float(delta[changed].mean()), "m")

print("Mean absolute change among changed cells:",
      float(np.abs(delta[changed]).mean()), "m")

print("95th percentile absolute change:",
      float(np.percentile(np.abs(delta[changed]), 95)), "m")

print("99th percentile absolute change:",
      float(np.percentile(np.abs(delta[changed]), 99)), "m")

print("\nThreshold analysis:")

for threshold in [1, 2, 5, 10, 15]:
    count = int((lowered & (delta <= -threshold)).sum())
    print(f"Lowered by at least {threshold} m: {count} cells")

# Extract all cells lowered by more than 5 metres
rows, cols = np.where(lowered & (delta < -5))

xs, ys = rasterio.transform.xy(transform, rows, cols)

report = pd.DataFrame({
    "row": rows,
    "column": cols,
    "easting": xs,
    "northing": ys,
    "original_elevation_m": before[rows, cols],
    "breached_elevation_m": after[rows, cols],
    "elevation_change_m": delta[rows, cols]
})

report = report.sort_values("elevation_change_m")

report.to_csv(OUTPUT, index=False)

print("\nCells lowered by more than 5 metres:", len(report))
print("Report saved:", OUTPUT)

print("\nMost severely lowered cells:")
print(report.head(20).to_string(index=False))

print("\nAssessment completed.")
