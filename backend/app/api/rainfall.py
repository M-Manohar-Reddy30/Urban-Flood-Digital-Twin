from datetime import date

from fastapi import APIRouter, HTTPException, Query

from backend.app.services.rainfall_service import get_rainfall_data

router = APIRouter(prefix="/api/v1/rainfall", tags=["Rainfall"])


@router.get("/summary")
def rainfall_summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
):
    """Get rainfall observations and statistics, optionally filtered by date."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be on or before end_date.",
        )

    try:
        return get_rainfall_data(start_date, end_date)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
