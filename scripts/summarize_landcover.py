
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]

RASTER_PATH = (
    ROOT / "data/raw/land_cover/"
    "ESA_WorldCover_10m_2021_v200_N15E075_Map.tif"
)
BOUNDARY_PATH = (
    ROOT / "data/processed/"
    "ballari_municipal_boundary_2d.geojson"
)
STATS_PATH = ROOT / "data/processed/ballari_landcover_statistics.csv"
MAP_PATH = ROOT / "data/processed/ballari_landcover_map.png"

CLASS_NAMES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}


def main():
    boundary = gpd.read_file(BOUNDARY_PATH)

    # Mask the original raster using the exact municipal polygon.
    with rasterio.open(RASTER_PATH) as src:
        boundary = boundary.to_crs(src.crs)

        clipped, transform = mask(
            src,
            boundary.geometry,
            crop=True,
            filled=False,
        )

        band = clipped[0]
        values, counts = np.unique(
            band.compressed(),
            return_counts=True,
        )

        total = int(counts.sum())

        if total == 0:
            raise ValueError(
                "No valid land-cover pixels found inside the boundary."
            )

        rows = [
            {
                "class_code": int(value),
                "class_name": CLASS_NAMES.get(
                    int(value), "Unknown"
                ),
                "pixel_count": int(count),
                "percentage": round(
                    float(count) / total * 100, 4
                ),
            }
            for value, count in zip(values, counts)
        ]

        stats = pd.DataFrame(rows)
        stats.to_csv(STATS_PATH, index=False)

        # Plot the categorical raster.
        class_codes = [int(value) for value in values]
        palette = plt.get_cmap("tab20", len(class_codes))
        colors = [palette(i) for i in range(len(class_codes))]
        cmap = ListedColormap(colors)
        cmap.set_bad((1, 1, 1, 0))

        masked = np.ma.masked_array(
            band.data,
            mask=np.ma.getmaskarray(band),
        )

        fig, ax = plt.subplots(figsize=(10, 10))

        ax.imshow(
            masked,
            cmap=cmap,
            interpolation="nearest",
            extent=(
                transform.c,
                transform.c + transform.a * band.shape[1],
                transform.f + transform.e * band.shape[0],
                transform.f,
            ),
        )

        boundary.plot(
            ax=ax,
            facecolor="none",
            edgecolor="black",
            linewidth=1.0,
        )

        ax.set_title(
            "Ballari City Corporation - ESA WorldCover 2021"
        )
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_aspect("equal")

        legend_items = [
            Patch(
                facecolor=colors[i],
                label=CLASS_NAMES.get(code, str(code)),
            )
            for i, code in enumerate(class_codes)
        ]

        ax.legend(
            handles=legend_items,
            loc="upper left",
            bbox_to_anchor=(1.02, 1),
        )

        fig.savefig(MAP_PATH, dpi=200, bbox_inches="tight")
        plt.close(fig)

    print("Saved statistics:", STATS_PATH)
    print("Saved map:", MAP_PATH)
    print("Valid pixels inside polygon:", total)
    print()
    print(stats.to_string(index=False))


if __name__ == "__main__":
    main()
