from pathlib import Path
import rasterio
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEM_DIR = ROOT / "data/raw/dem"

TILES = [
    "Copernicus_DSM_10_N15_00_E076_00_DEM.tif",
    "Copernicus_DSM_COG_10_N15_00_E077_00_DEM.tif",
    "Copernicus_DSM_COG_10_N14_00_E076_00_DEM.tif",
    "Copernicus_DSM_COG_10_N14_00_E077_00_DEM.tif",
]

all_valid = True

for filename in TILES:
    path = DEM_DIR / filename
    print(f"\n{'=' * 65}")
    print("TILE:", filename)

    if not path.exists():
        print("ERROR: File not found")
        all_valid = False
        continue

    try:
        with rasterio.open(path) as src:
            print("Driver:", src.driver)
            print("CRS:", src.crs)
            print("Dimensions:", src.width, "x", src.height)
            print("Resolution:", src.res)
            print("Bounds:", src.bounds)
            print("Data type:", src.dtypes[0])
            print("NoData:", src.nodata)
            print("File size:", round(path.stat().st_size / 1024 / 1024, 2), "MB")

            if src.crs is None or src.crs.to_epsg() != 4326:
                raise ValueError("Unexpected CRS; expected EPSG:4326")

            if src.width < 3000 or src.height < 3000:
                raise ValueError("Unexpectedly small raster dimensions")

            data = src.read(1, masked=True)
            values = data.compressed()

            if values.size == 0:
                raise ValueError("No valid elevation pixels")

            if not np.isfinite(values).all():
                raise ValueError("Non-finite elevation values detected")

            print("Valid pixels:", values.size)
            print("Minimum elevation:", round(float(values.min()), 2), "m")
            print("Maximum elevation:", round(float(values.max()), 2), "m")
            print("Mean elevation:", round(float(values.mean()), 2), "m")

            if values.min() < 0 or values.max() > 9000:
                raise ValueError("Elevation range requires investigation")

        print("STATUS: PASS")

    except Exception as exc:
        print("STATUS: FAIL")
        print("REASON:", exc)
        all_valid = False

print(f"\n{'=' * 65}")
print("FINAL RESULT:", "ALL TILES PASSED" if all_valid else "VALIDATION FAILED")

if not all_valid:
    raise SystemExit(1)
