from fastapi import APIRouter
from app.schemas.calendar import BurningCalendarResponse

router = APIRouter()

@router.get("/{aoi_id}", response_model=BurningCalendarResponse)
def get_burning_calendar(aoi_id: str, year: int = 2026):
    return {
        "aoi_id": aoi_id,
        "year": year,
        "status": "active",
        "peak_window_start": "02-15",
        "peak_window_end": "03-30",
        "daily_risk_levels": []
    }
