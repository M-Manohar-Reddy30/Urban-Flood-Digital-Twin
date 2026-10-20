from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

ROOT = Path(__file__).resolve().parents[1]

landcover_path = ROOT / "data/processed/ballari_landcover_2021.tif"
terrain_path = ROOT / "data/processed/dem/ballari_dem_utm43_corrected.tif"
output_path = ROOT / "data/processed/ballari_landcover_utm43_aligned.tif"

with rasterio.open(landcover_path) as landcover, \
     rasterio.open(terrain_path) as terrain:

    destination = np.zeros(
        (terrain.height, terrain.width),
        dtype=np.uint8,
    )

    reproject(
        source=rasterio.band(landcover, 1),
        destination=destination,
        src_transform=landcover.transform,
        src_crs=landcover.crs,
        src_nodata=landcover.nodata,
        dst_transform=terrain.transform,
        dst_crs=terrain.crs,
        dst_nodata=0,
        resampling=Resampling.nearest,
    )

    profile = terrain.profile.copy()
    profile.update(
        driver="GTiff",
        dtype="uint8",
        count=1,
        nodata=0,
        compress="deflate",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(destination, 1)

with rasterio.open(output_path) as result:
    values = result.read(1)
    classes, counts = np.unique(values[values != 0], return_counts=True)

    print("Saved:", output_path)
    print("CRS:", result.crs)
    print("Dimensions:", result.width, "x", result.height)
    print("Pixel size:", result.res)
    print("NoData:", result.nodata)
    print("Valid pixels:", int(np.count_nonzero(values)))
    print("Land-cover classes:", dict(zip(classes.tolist(), counts.tolist())))
