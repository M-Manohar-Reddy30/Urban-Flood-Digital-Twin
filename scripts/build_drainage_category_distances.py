from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

GRID = ROOT / "data/processed/ballari_gis_features.csv"
DRAINAGE = ROOT / "data/processed/drainage/ballari_drainage_clipped.geojson"

OUTPUT = (
    ROOT / "data/processed/susceptibility/"
    "ballari_gis_drainage_category_features.csv"
)

CRS = "EPSG:32643"


def nearest_category(points, drainage, category):
    subset = drainage[
        drainage["category"].astype(str).str.casefold()
        == category.casefold()
    ][["geometry"]].copy()

    if subset.empty:
        raise ValueError(f"No drainage features found for {category}")

    joined = gpd.sjoin_nearest(
        points,
        subset,
        how="left",
        distance_col="distance_m",
    )

    distances = (
        joined.groupby(level=0)["distance_m"]
        .min()
        .reindex(points.index)
    )

    if distances.isna().any() or not np.isfinite(distances).all():
        raise ValueError(f"Invalid distances for {category}")

    return distances


def main():
    grid = pd.read_csv(GRID)
    drainage = gpd.read_file(DRAINAGE)

    points = gpd.GeoDataFrame(
        grid.copy(),
        geometry=gpd.points_from_xy(
            grid["easting_m"], grid["northing_m"]
        ),
        crs=CRS,
    )

    drainage = drainage.to_crs(CRS)

    print("Calculating distance to mapped drains...")
    points["distance_to_mapped_drain_m"] = nearest_category(
        points, drainage, "Drain"
    )

    print("Calculating distance to mapped streams...")
    points["distance_to_mapped_stream_m"] = nearest_category(
        points, drainage, "Stream"
    )

    output = pd.DataFrame(points.drop(columns="geometry"))

    if len(output) != len(grid):
        raise ValueError("Output row count mismatch")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT, index=False)

    print("\nCATEGORY DISTANCE SUMMARY")
    for column in [
        "distance_to_mapped_drain_m",
        "distance_to_mapped_stream_m",
    ]:
        print(f"\n{column}")
        print(output[column].describe().round(2).to_string())

    print("\nRecords:", len(output))
    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
