from pathlib import Path
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[1]
DEM_DIR = ROOT / "data/raw/dem"
OUTPUT_DIR = ROOT / "data/processed/hydrology"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TILES = [
    DEM_DIR / "Copernicus_DSM_10_N15_00_E076_00_DEM.tif",
    DEM_DIR / "Copernicus_DSM_COG_10_N15_00_E077_00_DEM.tif",
    DEM_DIR / "Copernicus_DSM_COG_10_N14_00_E076_00_DEM.tif",
    DEM_DIR / "Copernicus_DSM_COG_10_N14_00_E077_00_DEM.tif",
]

BOUNDARY_FILE = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"
MOSAIC_FILE = OUTPUT_DIR / "copernicus_four_tile_mosaic.tif"
OUTPUT_FILE = OUTPUT_DIR / "ballari_hydrology_dem_30m_complete.tif"

TARGET_CRS = "EPSG:32643"
NODATA = -9999.0
BUFFER_METRES = 10000
RESOLUTION = 30


def main():
    for tile in TILES:
        if not tile.exists():
            raise FileNotFoundError(tile)

    print("\nSTEP 1: Creating four-tile mosaic")

    with rasterio.open(TILES[0]) as first:
        source_crs = first.crs

    if source_crs is None or source_crs.to_epsg() != 4326:
        raise ValueError("Expected source DEM tiles in EPSG:4326")

    with rasterio.open(TILES[0]) as src0, \
         rasterio.open(TILES[1]) as src1, \
         rasterio.open(TILES[2]) as src2, \
         rasterio.open(TILES[3]) as src3:

        mosaic, transform = merge(
            [src0, src1, src2, src3],
            nodata=NODATA,
            dtype="float32",
            resampling=Resampling.bilinear,
        )

        profile = src0.profile.copy()
        profile.update(
            driver="GTiff",
            height=mosaic.shape[1],
            width=mosaic.shape[2],
            transform=transform,
            crs=source_crs,
            count=1,
            dtype="float32",
            nodata=NODATA,
            compress="deflate",
            predictor=3,
            tiled=True,
            blockxsize=256,
            blockysize=256,
            BIGTIFF="IF_SAFER",
        )
        profile.pop("blockxsize", None)
        profile.pop("blockysize", None)
        profile["blockxsize"] = 256
        profile["blockysize"] = 256

    with rasterio.open(MOSAIC_FILE, "w", **profile) as dst:
        dst.write(mosaic[0], 1)

    valid = mosaic[0] != NODATA
    print("Mosaic saved:", MOSAIC_FILE)
    print("Dimensions:", mosaic.shape[2], "x", mosaic.shape[1])
    print("Valid pixels:", int(valid.sum()))
    print("Elevation range:", float(mosaic[0][valid].min()),
          "to", float(mosaic[0][valid].max()), "m")

    del mosaic

    print("\nSTEP 2: Preparing 10 km municipal buffer")

    boundary = gpd.read_file(BOUNDARY_FILE)

    if boundary.empty:
        raise ValueError("Municipal boundary is empty")

    if boundary.crs is None:
        raise ValueError("Municipal boundary CRS is missing")

    boundary_utm = boundary.to_crs(TARGET_CRS)
    municipal_geometry = boundary_utm.geometry.union_all()
    buffered_geometry = municipal_geometry.buffer(BUFFER_METRES)

    buffer_gdf = gpd.GeoDataFrame(
        geometry=[buffered_geometry],
        crs=TARGET_CRS,
    ).to_crs("EPSG:4326")

    print("Municipal boundary CRS:", boundary.crs)
    print("Buffer distance:", BUFFER_METRES, "metres")

    print("\nSTEP 3: Clipping mosaic to buffered study area")

    with rasterio.open(MOSAIC_FILE) as src:
        clipped, clipped_transform = mask(
            src,
            [mapping(buffer_gdf.geometry.iloc[0])],
            crop=True,
            filled=True,
            nodata=NODATA,
        )
        clipped_profile = src.profile.copy()
        clipped_profile.update(
            height=clipped.shape[1],
            width=clipped.shape[2],
            transform=clipped_transform,
            nodata=NODATA,
        )

    clipped_file = OUTPUT_DIR / "ballari_hydrology_dem_clipped_4326.tif"

    with rasterio.open(clipped_file, "w", **clipped_profile) as dst:
        dst.write(clipped)

    print("Clipped source saved:", clipped_file)
    print("Clipped dimensions:", clipped.shape[2], "x", clipped.shape[1])

    print("\nSTEP 4: Reprojecting to EPSG:32643 at 30 m")

    with rasterio.open(clipped_file) as src:
        transform, width, height = calculate_default_transform(
            src.crs,
            TARGET_CRS,
            src.width,
            src.height,
            *src.bounds,
            resolution=RESOLUTION,
        )

        destination = np.full(
            (height, width),
            NODATA,
            dtype=np.float32,
        )

        reproject(
            source=rasterio.band(src, 1),
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=NODATA,
            dst_transform=transform,
            dst_crs=TARGET_CRS,
            dst_nodata=NODATA,
            resampling=Resampling.bilinear,
            init_dest_nodata=True,
        )

        output_profile = src.profile.copy()
        output_profile.update(
            driver="GTiff",
            crs=TARGET_CRS,
            transform=transform,
            width=width,
            height=height,
            count=1,
            dtype="float32",
            nodata=NODATA,
            compress="deflate",
            predictor=3,
            tiled=True,
            BIGTIFF="IF_SAFER",
        )

    with rasterio.open(OUTPUT_FILE, "w", **output_profile) as dst:
        dst.write(destination, 1)

    valid = destination != NODATA

    print("\nSTEP 5: Final DEM summary")
    print("Output:", OUTPUT_FILE)
    print("CRS:", TARGET_CRS)
    print("Resolution:", RESOLUTION, "m")
    print("Dimensions:", width, "x", height)
    print("Valid pixels:", int(valid.sum()))
    print("NoData pixels:", int((~valid).sum()))

    if valid.any():
        print("Minimum elevation:", round(float(destination[valid].min()), 2), "m")
        print("Maximum elevation:", round(float(destination[valid].max()), 2), "m")
        print("Mean elevation:", round(float(destination[valid].mean()), 2), "m")

    print("\nDEM reconstruction completed.")


if __name__ == "__main__":
    main()
