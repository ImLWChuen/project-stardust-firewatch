from fastapi import APIRouter
from app.schemas.anomaly import AnomalySummaryResponse

router = APIRouter()

@router.get("/{aoi_id}", response_model=AnomalySummaryResponse)
def get_anomalies(aoi_id: str):
    """Return the anomaly summary for the given area of interest."""
    return {"aoi_id": aoi_id, "active_anomalies_count": 0, "severity": "low"}
