from pathlib import Path

import geopandas as gpd
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.io import MemoryFile

ROOT = Path(__file__).resolve().parents[1]

source = ROOT / "data/raw/dem/Copernicus_DSM_10_N15_00_E076_00_DEM.tif"
boundary_path = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"
output = ROOT / "data/processed/dem/ballari_dem_utm43_corrected.tif"

boundary = gpd.read_file(boundary_path)

with rasterio.open(source) as src:
    boundary = boundary.to_crs("EPSG:32643")

    transform, width, height = calculate_default_transform(
        src.crs, "EPSG:32643",
        src.width, src.height, *src.bounds,
        resolution=30
    )

    profile = src.profile.copy()
    profile.update(
        crs="EPSG:32643",
        transform=transform,
        width=width,
        height=height,
        nodata=-9999.0,
        dtype="float32",
        compress="deflate"
    )

    with MemoryFile() as memfile:
        with memfile.open(**profile) as projected:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(projected, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs="EPSG:32643",
                src_nodata=src.nodata,
                dst_nodata=-9999.0,
                resampling=Resampling.bilinear
            )

            clipped, clipped_transform = mask(
                projected,
                boundary.geometry,
                crop=True,
                nodata=-9999.0,
                filled=True
            )

            out_profile = projected.profile.copy()
            out_profile.update(
                height=clipped.shape[1],
                width=clipped.shape[2],
                transform=clipped_transform,
                nodata=-9999.0
            )

            output.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(output, "w", **out_profile) as dst:
                dst.write(clipped)

print("Saved corrected DEM:", output)
with rasterio.open(output) as result:
    print("CRS:", result.crs)
    print("Dimensions:", result.width, "x", result.height)
    print("Bounds:", result.bounds)
    print("Resolution:", result.res)
    print("NoData:", result.nodata)
