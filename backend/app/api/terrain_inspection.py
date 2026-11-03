"""Inspect provisional environmental features at a map location."""

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import math

import geopandas as gpd
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import Point

router = APIRouter(prefix="/api/v1/gis", tags=["Terrain inspection"])
ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/processed/terrain_inspection"
BOUNDARY = ROOT / "data/processed/ballari_municipal_boundary_2d.geojson"

FIELDS = [
    "longitude", "latitude", "easting_m", "northing_m",
    "elevation_m", "slope_degrees", "landcover_class",
    "distance_to_mapped_drain_m", "distance_to_mapped_stream_m",
    "flow_accumulation_cells", "upstream_contributing_area_km2",
]
TO_METRIC = Transformer.from_crs(
    "EPSG:4326", "EPSG:32643", always_xy=True
)


@lru_cache(maxsize=1)
def load_dataset():
    path = DATA / "ballari_terrain_drainage_hydrology.csv"
    metadata = json.loads(
        (DATA / "metadata.json").read_text(encoding="utf-8")
    )
    if metadata.get("coordinate_reference_system") != "EPSG:32643":
        raise ValueError("Unexpected dataset CRS.")
    if hashlib.sha256(path.read_bytes()).hexdigest() != metadata.get("output_sha256"):
        raise ValueError("Dataset checksum mismatch.")

    frame = pd.read_csv(path)
    if frame.empty or not set(FIELDS).issubset(frame.columns):
        raise ValueError("Invalid dataset schema.")
    for column in FIELDS:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if not np.isfinite(frame[FIELDS].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite dataset values.")

    coordinates = frame[["easting_m", "northing_m"]].to_numpy()
    if frame.duplicated(["easting_m", "northing_m"]).any():
        raise ValueError("Duplicate coordinates.")

    boundary = gpd.read_file(BOUNDARY).to_crs("EPSG:32643")
    city = boundary.geometry.union_all()
    if city.is_empty or not city.is_valid:
        raise ValueError("Invalid boundary.")

    return frame, coordinates, cKDTree(coordinates), city


@router.get("/terrain-inspection")
def inspect_terrain(
    longitude: float = Query(..., ge=-180, le=180),
    latitude: float = Query(..., ge=-90, le=90),
):
    if not math.isfinite(longitude) or not math.isfinite(latitude):
        raise HTTPException(status_code=422, detail="Coordinates must be finite.")

    try:
        frame, coordinates, tree, city = load_dataset()
    except OSError as exc:
        raise HTTPException(
            status_code=503, detail="Terrain inspection data is unavailable."
        ) from exc
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=500, detail="Terrain inspection data is invalid."
        ) from exc

    x, y = TO_METRIC.transform(longitude, latitude)
    if not math.isfinite(x) or not math.isfinite(y) or not city.covers(Point(x, y)):
        raise HTTPException(
            status_code=404, detail="Location is outside the municipal boundary."
        )

    distance, index = tree.query([x, y])
    centre = coordinates[index]

    # Existing GIS cells are north-up 30 m squares.
    # Reject gaps instead of returning a distant neighbouring cell.
    if np.any(np.abs(centre - [x, y]) > 15.000001):
        raise HTTPException(
            status_code=404, detail="No available feature cell at this location."
        )

    row = frame.iloc[int(index)]
    values = {field: float(row[field]) for field in FIELDS}
    values["landcover_class"] = int(row["landcover_class"])

    return {
        "status": "provisional_environmental_features",
        "query": {"longitude": longitude, "latitude": latitude},
        "cell_centre_distance_m": round(float(distance), 3),
        "gis_cell_size_m": 30,
        "values": values,
        "note": (
            "Values describe the selected GIS cell. Hydrology was sampled "
            "from the hydrology cell containing its centre. These are not "
            "flood probabilities, flood depths or drainage-capacity estimates."
        ),
    }
