from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

GRID_FILE = ROOT / "data/processed/ballari_gis_features.csv"
DRAINAGE_FILE = ROOT / "data/processed/drainage/ballari_drainage_clipped.geojson"

OUTPUT_DIR = ROOT / "data/processed/susceptibility"
OUTPUT_FILE = OUTPUT_DIR / "ballari_gis_drainage_features.csv"

METRIC_CRS = "EPSG:32643"


def main():
    print("BALLARI DRAINAGE PROXIMITY ANALYSIS")
    print("=" * 60)

    grid = pd.read_csv(GRID_FILE)
    drainage = gpd.read_file(DRAINAGE_FILE)

    required = {
        "longitude", "latitude", "easting_m", "northing_m",
        "elevation_m", "slope_degrees", "landcover_class"
    }

    missing = required - set(grid.columns)
    if missing:
        raise ValueError(f"Missing GIS columns: {sorted(missing)}")

    if drainage.empty:
        raise ValueError("Drainage dataset is empty.")

    if drainage.crs is None:
        raise ValueError("Drainage CRS is missing.")

    if not drainage.geometry.is_valid.all():
        raise ValueError("Invalid drainage geometry detected.")

    print("GIS points:", len(grid))
    print("Drainage features:", len(drainage))

    points = gpd.GeoDataFrame(
        grid.copy(),
        geometry=gpd.points_from_xy(
            grid["easting_m"], grid["northing_m"]
        ),
        crs=METRIC_CRS,
    )

    drainage = drainage.to_crs(METRIC_CRS)

    drainage_columns = [
        column for column in ["source_id", "category", "geometry"]
        if column in drainage.columns
    ]

    drainage = drainage[drainage_columns].copy()

    print("Calculating nearest drainage distances...")

    result = gpd.sjoin_nearest(
        points,
        drainage,
        how="left",
        distance_col="nearest_drainage_distance_m",
    )

    # Resolve exact-distance ties deterministically.
    result = result.reset_index(names="grid_row")

    sort_columns = ["grid_row", "nearest_drainage_distance_m"]
    if "source_id" in result.columns:
        sort_columns.append("source_id")

    result = (
        result.sort_values(sort_columns, kind="stable")
        .drop_duplicates(subset="grid_row", keep="first")
        .sort_values("grid_row")
    )

    output_columns = [
        "longitude",
        "latitude",
        "easting_m",
        "northing_m",
        "elevation_m",
        "slope_degrees",
        "landcover_class",
        "nearest_drainage_distance_m",
    ]

    for column in ["category", "source_id"]:
        if column in result.columns:
            output_columns.append(column)

    output = pd.DataFrame(result[output_columns]).copy()

    distances = pd.to_numeric(
        output["nearest_drainage_distance_m"],
        errors="coerce"
    )

    if len(output) != len(grid):
        raise ValueError(
            f"Output row mismatch: {len(output)} != {len(grid)}"
        )

    if not np.isfinite(distances).all() or (distances < 0).any():
        raise ValueError("Invalid nearest-drainage distances.")

    if output["nearest_drainage_distance_m"].isna().any():
        raise ValueError("Some GIS points have no nearest drainage feature.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_FILE, index=False)

    print("\nDRAINAGE PROXIMITY SUMMARY")
    print("=" * 60)
    print("Output records:", len(output))
    print("Minimum distance (m):", round(float(distances.min()), 2))
    print("Median distance (m):", round(float(distances.median()), 2))
    print("Mean distance (m):", round(float(distances.mean()), 2))
    print("Maximum distance (m):", round(float(distances.max()), 2))

    print("\nNearest feature categories:")
    if "category" in output.columns:
        print(output["category"].value_counts(dropna=False).to_string())

    print("\nSaved:", OUTPUT_FILE)
    print(
        "Interpretation: distance to mapped source linework, "
        "not verified drainage capacity or flood probability."
    )


if __name__ == "__main__":
    main()
