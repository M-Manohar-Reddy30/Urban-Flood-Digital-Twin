import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.app.services.gis_service import get_gis_summary

router = APIRouter(prefix="/api/v1/gis", tags=["GIS"])

BOUNDARY_FILE = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "processed"
    / "ballari_municipal_boundary_2d.geojson"
)


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

    if boundary.get("type") not in {"Feature", "FeatureCollection"}:
        raise HTTPException(
            status_code=500,
            detail="Unexpected municipal boundary GeoJSON format.",
        )

    return boundary
