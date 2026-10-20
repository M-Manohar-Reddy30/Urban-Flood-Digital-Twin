from pathlib import Path

import geopandas as gpd
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "processed"


def get_gis_summary() -> dict:
    """Return summary information for the prepared Ballari GIS dataset."""
    csv_path = DATA_DIR / "ballari_gis_features.csv"
    boundary_path = DATA_DIR / "ballari_municipal_boundary_2d.geojson"

    if not csv_path.exists():
        raise FileNotFoundError(f"GIS dataset not found: {csv_path}")

    if not boundary_path.exists():
        raise FileNotFoundError(f"Municipal boundary not found: {boundary_path}")

    features = pd.read_csv(csv_path)
    boundary = gpd.read_file(boundary_path)

    required_columns = {
        "longitude",
        "latitude",
        "elevation_m",
        "slope_degrees",
        "landcover_class",
    }
    missing = required_columns - set(features.columns)

    if missing:
        raise ValueError(f"GIS dataset is missing columns: {sorted(missing)}")

    return {
        "city": "Ballari",
        "dataset": "ballari_gis_features.csv",
        "feature_count": int(len(features)),
        "coordinate_reference_system": str(boundary.crs),
        "boundary_feature_count": int(len(boundary)),
        "boundary_valid": bool(boundary.geometry.is_valid.all()),
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
