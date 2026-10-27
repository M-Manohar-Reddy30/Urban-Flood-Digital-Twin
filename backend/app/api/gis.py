import json
import math
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.app.services.gis_service import get_gis_summary

router = APIRouter(prefix="/api/v1/gis", tags=["GIS"])

DRAINAGE_FILE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "processed"
    / "drainage"
    / "ballari_drainage_clipped.geojson"
)

BOUNDARY_FILE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "processed"
    / "ballari_municipal_boundary_2d.geojson"
)


def _validate_geojson(data: dict, *, allowed_geometry_types: set[str]) -> bool:
    """Validate GeoJSON feature structure and coordinate values."""
    if not isinstance(data, dict):
        return False

    if data.get("type") == "Feature":
        features = [data]
    elif data.get("type") == "FeatureCollection":
        features = data.get("features")
        if not isinstance(features, list) or not features:
            return False
    else:
        return False

    def valid_position(position):
        return (
            isinstance(position, (list, tuple))
            and len(position) >= 2
            and isinstance(position[0], (int, float))
            and not isinstance(position[0], bool)
            and isinstance(position[1], (int, float))
            and not isinstance(position[1], bool)
            and math.isfinite(position[0])
            and math.isfinite(position[1])
            and -180 <= position[0] <= 180
            and -90 <= position[1] <= 90
        )

    def validate_coordinates(geometry_type, coordinates):
        if geometry_type == "Point":
            return valid_position(coordinates)

        if geometry_type in {"MultiPoint", "LineString"}:
            if not isinstance(coordinates, list):
                return False
            if geometry_type == "LineString" and len(coordinates) < 2:
                return False
            return all(valid_position(point) for point in coordinates)

        if geometry_type == "MultiLineString":
            return (
                isinstance(coordinates, list)
                and len(coordinates) > 0
                and all(
                    isinstance(line, list)
                    and len(line) >= 2
                    and all(valid_position(point) for point in line)
                    for line in coordinates
                )
            )

        if geometry_type == "Polygon":
            return (
                isinstance(coordinates, list)
                and len(coordinates) > 0
                and all(
                    isinstance(ring, list)
                    and len(ring) >= 4
                    and ring[0] == ring[-1]
                    and all(valid_position(point) for point in ring)
                    for ring in coordinates
                )
            )

        if geometry_type == "MultiPolygon":
            return (
                isinstance(coordinates, list)
                and len(coordinates) > 0
                and all(
                    validate_coordinates("Polygon", polygon)
                    for polygon in coordinates
                )
            )

        return False

    for feature in features:
        if not isinstance(feature, dict):
            return False

        if feature.get("type") != "Feature":
            return False

        properties = feature.get("properties")
        if properties is not None and not isinstance(properties, dict):
            return False

        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            return False

        geometry_type = geometry.get("type")
        if geometry_type not in allowed_geometry_types:
            return False

        if not validate_coordinates(
            geometry_type, geometry.get("coordinates")
        ):
            return False

    return True


@router.get("/summary")
def gis_summary():
    try:
        return get_gis_summary()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/boundary")
def gis_boundary():
    try:
        with BOUNDARY_FILE.open("r", encoding="utf-8") as file:
            boundary = json.load(file)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Municipal boundary GeoJSON is unavailable.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Municipal boundary GeoJSON is invalid.",
        ) from exc

    if not _validate_geojson(
        boundary,
        allowed_geometry_types={"Polygon", "MultiPolygon"},
    ):
        raise HTTPException(
            status_code=500,
            detail="Municipal boundary GeoJSON has invalid features or geometries.",
        )

    return boundary


@router.get("/drainage")
def gis_drainage():
    """Return the clipped Ballari drainage network as GeoJSON."""
    try:
        with DRAINAGE_FILE.open("r", encoding="utf-8") as file:
            drainage = json.load(file)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Drainage GeoJSON is unavailable. Run the drainage dataset builder first.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Drainage GeoJSON is invalid.",
        ) from exc

    if not _validate_geojson(
        drainage,
        allowed_geometry_types={"LineString", "MultiLineString"},
    ):
        raise HTTPException(
            status_code=500,
            detail="Drainage GeoJSON has invalid features or geometries.",
        )

    return drainage
