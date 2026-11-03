from pathlib import Path
import rasterio

ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data/processed/hydrology/ballari_hydrology_dem_30m_complete.tif"
OUTPUT_DIR = ROOT / "data/processed/hydrology/conditioning"
OUTPUT = OUTPUT_DIR / "ballari_dem_whitebox_input.tif"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with rasterio.open(SOURCE) as src:
    profile = src.profile.copy()

    profile.update(
        driver="GTiff",
        dtype="float32",
        compress="NONE",
        predictor=1,
        tiled=False,
        BIGTIFF="IF_SAFER"
    )

    with rasterio.open(OUTPUT, "w", **profile) as dst:
        for _, window in src.block_windows(1):
            dst.write(src.read(1, window=window), 1, window=window)

print("Whitebox-compatible DEM created:", OUTPUT)

with rasterio.open(SOURCE) as original, rasterio.open(OUTPUT) as copied:
    print("Original CRS:", original.crs)
    print("Copied CRS:", copied.crs)
    print("Original dimensions:", original.width, original.height)
    print("Copied dimensions:", copied.width, copied.height)
    print("Original resolution:", original.res)
    print("Copied resolution:", copied.res)
    print("Original NoData:", original.nodata)
    print("Copied NoData:", copied.nodata)
    print("Output compression:", copied.compression)
    print("Output predictor:", copied.profile.get("predictor"))

    if not (
        original.crs == copied.crs
        and original.transform == copied.transform
        and original.width == copied.width
        and original.height == copied.height
        and original.nodata == copied.nodata
    ):
        raise RuntimeError("Raster metadata mismatch")

print("Preparation completed.")
