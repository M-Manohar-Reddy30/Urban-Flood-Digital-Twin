from datetime import date

from fastapi import APIRouter, HTTPException, Query

from backend.app.services.spatial_rainfall_service import (
    get_municipal_rainfall,
    get_spatial_rainfall_quality,
)

router = APIRouter(
    prefix="/api/v1/rainfall/spatial",
    tags=["Spatial Rainfall"],
)


@router.get("/summary")
def spatial_rainfall_summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
):
    """Return area-weighted municipal rainfall and grid-cell observations."""

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be on or before end_date.",
        )

    try:
        return get_municipal_rainfall(start_date, end_date)

    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/quality")
def spatial_rainfall_quality():
    """Return structural and spatial coverage quality indicators."""

    try:
        return get_spatial_rainfall_quality()

    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
