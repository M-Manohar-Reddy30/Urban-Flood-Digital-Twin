from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
boundary_path = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"

layers = [
    (
        ROOT / "data/processed/dem/ballari_dem_utm43_corrected.tif",
        ROOT / "data/processed/ballari_elevation_map.png",
        "Ballari Elevation (m)",
        "terrain",
    ),
    (
        ROOT / "data/processed/slope/ballari_slope_degrees_corrected.tif",
        ROOT / "data/processed/ballari_slope_map_corrected.png",
        "Ballari Terrain Slope (degrees)",
        "viridis",
    ),
]

boundary = gpd.read_file(boundary_path)

for raster_path, output_path, title, palette in layers:
    with rasterio.open(raster_path) as src:
        data = src.read(1, masked=True)
        extent = (
            src.bounds.left,
            src.bounds.right,
            src.bounds.bottom,
            src.bounds.top,
        )
        raster_crs = src.crs

    boundary_projected = boundary.to_crs(raster_crs)

    fig, ax = plt.subplots(figsize=(10, 8))
    image = ax.imshow(
        data,
        extent=extent,
        origin="upper",
        cmap=palette,
        interpolation="nearest",
    )
    boundary_projected.boundary.plot(
        ax=ax, color="black", linewidth=0.8
    )
    fig.colorbar(image, ax=ax, shrink=0.75, label=title)
    ax.set_title(title)
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    ax.set_aspect("equal")
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Saved:", output_path)
