from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject
from rasterio.enums import Resampling
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data/raw/dem/Copernicus_DSM_10_N15_00_E076_00_DEM.tif"
BOUNDARY = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"

OUTPUT_DIR = ROOT / "data/processed/hydrology"
OUTPUT = OUTPUT_DIR / "ballari_hydrology_dem_30m.tif"

TARGET_CRS = "EPSG:32643"
BUFFER_METRES = 10000
NODATA = -9999.0


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    boundary = gpd.read_file(BOUNDARY)

    if boundary.crs is None:
        raise ValueError("Municipal boundary CRS is missing.")

    boundary = boundary.to_crs(TARGET_CRS)
    city_geometry = boundary.geometry.union_all()
    buffered_geometry = city_geometry.buffer(BUFFER_METRES)

    # Critical fix: transform buffered geometry into source DEM CRS.
    source_geometry = (
        gpd.GeoSeries([buffered_geometry], crs=TARGET_CRS)
        .to_crs("EPSG:4326")
        .iloc[0]
    )

    with rasterio.open(SOURCE) as src:
        print("Source DEM CRS:", src.crs)
        print("Buffered geometry CRS:", "EPSG:4326")

        clipped, clipped_transform = mask(
            src,
            [mapping(source_geometry)],
            crop=True,
            filled=False,
        )

        source_data = clipped[0]
        source_valid = ~np.ma.getmaskarray(source_data)

        if not source_valid.any():
            raise ValueError("No valid DEM pixels in buffered area.")

        source_data = source_data.astype("float32").filled(NODATA)

        bounds = rasterio.transform.array_bounds(
            clipped.shape[1],
            clipped.shape[2],
            clipped_transform,
        )

        dst_transform, width, height = calculate_default_transform(
            src.crs,
            TARGET_CRS,
            clipped.shape[2],
            clipped.shape[1],
            *bounds,
            resolution=30,
        )

        destination = np.full(
            (height, width), NODATA, dtype="float32"
        )

        reproject(
            source=source_data,
            destination=destination,
            src_transform=clipped_transform,
            src_crs=src.crs,
            src_nodata=NODATA,
            dst_transform=dst_transform,
            dst_crs=TARGET_CRS,
            dst_nodata=NODATA,
            resampling=Resampling.bilinear,
            init_dest_nodata=True,
        )

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": TARGET_CRS,
        "transform": dst_transform,
        "nodata": NODATA,
        "compress": "deflate",
        "predictor": 3,
        "tiled": True,
    }

    with rasterio.open(OUTPUT, "w", **profile) as dst:
        dst.write(destination, 1)

    valid = np.isfinite(destination) & (destination != NODATA)

    print("\nHYDROLOGY DEM CREATED")
    print("=" * 55)
    print("Output:", OUTPUT)
    print("CRS:", TARGET_CRS)
    print("Dimensions:", width, "x", height)
    print("Resolution:", dst_transform.a, abs(dst_transform.e))
    print("Valid pixels:", int(valid.sum()))
    print("NoData pixels:", int((~valid).sum()))
    print("Coverage:", round(valid.mean() * 100, 2), "%")

    if valid.any():
        print("Minimum elevation:", round(float(destination[valid].min()), 2))
        print("Maximum elevation:", round(float(destination[valid].max()), 2))

    print("Buffer:", BUFFER_METRES, "metres")
    print("Original DEM unchanged.")


if __name__ == "__main__":
    main()
