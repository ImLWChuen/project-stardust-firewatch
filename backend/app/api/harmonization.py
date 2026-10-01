from fastapi import APIRouter
from app.schemas.harmonization import HarmonizationStatusResponse

router = APIRouter()

@router.get("/status", response_model=HarmonizationStatusResponse)
def get_harmonization_status():
    return {"status": "synced", "model_version": "v1.2-calibrated"}
