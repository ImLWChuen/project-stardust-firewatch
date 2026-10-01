from fastapi import APIRouter
from app.schemas.hotspot import HotspotListResponse

router = APIRouter()

@router.get("/", response_model=HotspotListResponse)
def get_hotspots(aoi_id: str = None, start_date: str = None, end_date: str = None):
    return {"count": 0, "hotspots": []}
