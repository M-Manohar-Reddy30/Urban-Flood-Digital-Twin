from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, box

ROOT = Path(__file__).resolve().parents[1]

BOUNDARY_FILE = (
    ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"
)

OUTPUT_FILE = (
    ROOT / "data/processed/rainfall/"
    "ballari_imerg_grid_weights.csv"
)

PROJECTED_CRS = "EPSG:32643"
GRID_RESOLUTION = 0.1


def main():
    boundary_gdf = gpd.read_file(BOUNDARY_FILE)

    if boundary_gdf.empty:
        raise ValueError("Municipal boundary is empty.")

    if boundary_gdf.crs is None:
        raise ValueError("Municipal boundary CRS is missing.")

    boundary_gdf = boundary_gdf.to_crs("EPSG:4326")

    boundary = boundary_gdf.geometry.union_all()

    if boundary.is_empty or not boundary.is_valid:
        raise ValueError("Municipal boundary is empty or invalid.")

    projected_boundary = (
        boundary_gdf.to_crs(PROJECTED_CRS)
        .geometry.union_all()
    )

    boundary_area = projected_boundary.area / 1_000_000

    min_lon, min_lat, max_lon, max_lat = boundary.bounds

    latitudes = np.arange(-89.95, 90, GRID_RESOLUTION)
    longitudes = np.arange(-179.95, 180, GRID_RESOLUTION)

    candidate_lats = latitudes[
        (latitudes >= min_lat - GRID_RESOLUTION)
        & (latitudes <= max_lat + GRID_RESOLUTION)
    ]

    candidate_lons = longitudes[
        (longitudes >= min_lon - GRID_RESOLUTION)
        & (longitudes <= max_lon + GRID_RESOLUTION)
    ]

    records = []

    for latitude in candidate_lats:
        for longitude in candidate_lons:
            latitude = round(float(latitude), 2)
            longitude = round(float(longitude), 2)

            cell = box(
                longitude - 0.05,
                latitude - 0.05,
                longitude + 0.05,
                latitude + 0.05,
            )

            if not cell.intersects(boundary):
                continue

            projected_cell = (
                gpd.GeoSeries([cell], crs="EPSG:4326")
                .to_crs(PROJECTED_CRS)
                .iloc[0]
            )

            intersection = projected_cell.intersection(
                projected_boundary
            )

            area_km2 = intersection.area / 1_000_000

            if area_km2 <= 0:
                continue

            records.append({
                "grid_id": (
                    f"IMERG_{latitude:.2f}_{longitude:.2f}"
                ),
                "latitude": latitude,
                "longitude": longitude,
                "intersection_area_km2": area_km2,
                "centre_inside_boundary": boundary.covers(
                    Point(longitude, latitude)
                ),
            })

    df = pd.DataFrame(records)

    if df.empty:
        raise RuntimeError("No intersecting IMERG grid cells found.")

    total_intersection = df["intersection_area_km2"].sum()

    if not np.isclose(
        total_intersection,
        boundary_area,
        rtol=0.001,
    ):
        raise ValueError(
            "Grid intersections do not account for the complete "
            f"municipal area. Boundary={boundary_area:.6f}, "
            f"intersections={total_intersection:.6f} km2"
        )

    df["area_weight"] = (
        df["intersection_area_km2"] / total_intersection
    )

    df["boundary_area_km2"] = boundary_area
    df["grid_resolution_degrees"] = GRID_RESOLUTION

    df = df.sort_values(
        "intersection_area_km2",
        ascending=False,
    ).reset_index(drop=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print("\nBALLARI IMERG GRID WEIGHTS")
    print("=" * 65)
    print(df.to_string(index=False))

    print("\nSUMMARY")
    print("Grid cells:", len(df))
    print("Municipal area:", round(boundary_area, 4), "km2")
    print("Intersection area:", round(total_intersection, 4), "km2")
    print("Weight sum:", df["area_weight"].sum())
    print("Centres inside boundary:",
          int(df["centre_inside_boundary"].sum()))

    print("\nSaved:", OUTPUT_FILE.relative_to(ROOT))


if __name__ == "__main__":
    main()
