
from fastapi import APIRouter, HTTPException

from backend.app.services.readiness_service import get_readiness_summary


router = APIRouter(
    prefix="/api/v1/readiness",
    tags=["Data Readiness"],
)


@router.get("/summary")
def readiness_summary():
    try:
        return get_readiness_summary()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
