from fastapi import APIRouter

router = APIRouter()

@router.get("/{aoi_id}")
def get_critical_periods(aoi_id: str):
    """Return the known critical burning periods for the given area of interest."""
    return [
        {
            "aoi_id": aoi_id,
            "period_name": "Post-Harvest Burning Window",
            "start_date": "2026-02-15",
            "end_date": "2026-03-30",
            "risk_tier": "critical",
            "is_active_now": True
        }
    ]
