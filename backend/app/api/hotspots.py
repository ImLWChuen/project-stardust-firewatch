from fastapi import APIRouter
from app.schemas.hotspot import HotspotListResponse

router = APIRouter()

@router.get("/", response_model=HotspotListResponse)
def get_hotspots(aoi_id: str = None, start_date: str = None, end_date: str = None):
    """Return fire hotspots optionally filtered by area of interest and date range."""
    return {"count": 0, "hotspots": []}
