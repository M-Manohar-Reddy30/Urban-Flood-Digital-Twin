from fastapi import APIRouter, HTTPException

from backend.app.services.gis_service import get_gis_summary

router = APIRouter(prefix="/api/v1/gis", tags=["GIS"])


@router.get("/summary")
def gis_summary():
    try:
        return get_gis_summary()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
