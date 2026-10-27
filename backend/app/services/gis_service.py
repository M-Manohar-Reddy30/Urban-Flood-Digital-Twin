from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "processed"


def get_gis_summary() -> dict:
    """Return summary information after validating the prepared GIS data."""
    csv_path = DATA_DIR / "ballari_gis_features.csv"
    boundary_path = DATA_DIR / "ballari_municipal_boundary_2d.geojson"

    if not csv_path.exists():
        raise FileNotFoundError(f"GIS dataset not found: {csv_path}")

    if not boundary_path.exists():
        raise FileNotFoundError(
            f"Municipal boundary not found: {boundary_path}"
        )

    features = pd.read_csv(csv_path)
    boundary = gpd.read_file(boundary_path)

    required_columns = {
        "longitude",
        "latitude",
        "easting_m",
        "northing_m",
        "elevation_m",
        "slope_degrees",
        "landcover_class",
    }
    missing = required_columns - set(features.columns)

    if missing:
        raise ValueError(
            f"GIS dataset is missing columns: {sorted(missing)}"
        )

    if features.empty:
        raise ValueError("GIS dataset is empty.")

    numeric_columns = [
        "longitude",
        "latitude",
        "easting_m",
        "northing_m",
        "elevation_m",
        "slope_degrees",
        "landcover_class",
    ]

    for column in numeric_columns:
        features[column] = pd.to_numeric(
            features[column], errors="coerce"
        )

        values = features[column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(
                f"GIS dataset contains invalid or non-finite {column} values."
            )

    if not features["longitude"].between(-180, 180).all():
        raise ValueError("GIS dataset contains invalid longitude values.")

    if not features["latitude"].between(-90, 90).all():
        raise ValueError("GIS dataset contains invalid latitude values.")

    if (features["slope_degrees"] < 0).any() or (
        features["slope_degrees"] > 90
    ).any():
        raise ValueError(
            "GIS dataset contains invalid slope values; expected 0 to 90 degrees."
        )

    landcover = features["landcover_class"]
    if (
        (landcover < 0).any()
        or ((landcover % 1) != 0).any()
    ):
        raise ValueError(
            "GIS dataset contains invalid landcover class values."
        )

    if boundary.empty:
        raise ValueError("Municipal boundary dataset is empty.")

    if boundary.crs is None:
        raise ValueError("Municipal boundary CRS is missing.")

    if (
        boundary.geometry.isna().any()
        or boundary.geometry.is_empty.any()
        or not boundary.geometry.is_valid.all()
    ):
        raise ValueError(
            "Municipal boundary contains missing, empty, or invalid geometries."
        )

    return {
        "city": "Ballari",
        "dataset": "ballari_gis_features.csv",
        "feature_count": int(len(features)),
        "coordinate_reference_system": str(boundary.crs),
        "boundary_feature_count": int(len(boundary)),
        "boundary_valid": True,
        "elevation_m": {
            "min": round(float(features["elevation_m"].min()), 2),
            "max": round(float(features["elevation_m"].max()), 2),
            "mean": round(float(features["elevation_m"].mean()), 2),
        },
        "slope_degrees": {
            "min": round(float(features["slope_degrees"].min()), 2),
            "max": round(float(features["slope_degrees"].max()), 2),
            "mean": round(float(features["slope_degrees"].mean()), 2),
        },
        "landcover_class_counts": {
            str(int(key)): int(value)
            for key, value in features["landcover_class"]
            .value_counts()
            .sort_index()
            .items()
        },
        "note": (
            "These are GIS terrain and land-cover features, "
            "not validated flood predictions."
        ),
    }
