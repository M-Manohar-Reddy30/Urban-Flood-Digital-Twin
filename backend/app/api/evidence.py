from fastapi import APIRouter, HTTPException

from backend.app.services.evidence_service import get_evidence_summary

router = APIRouter(
    prefix="/api/v1/evidence",
    tags=["Flood Evidence"],
)


@router.get("/summary")
def evidence_summary():
    try:
        return get_evidence_summary()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
