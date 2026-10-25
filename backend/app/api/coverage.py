from fastapi import APIRouter

router = APIRouter()

@router.get("/{aoi_id}")
def get_coverage(aoi_id: str):
    """Return satellite overpass coverage metrics for the given area of interest."""
    return {
        "aoi_id": aoi_id,
        "overpass_count_24h": 4,
        "sensors": ["MODIS_TERRA", "MODIS_AQUA", "VIIRS_SNPP", "VIIRS_NOAA20"],
        "coverage_quality_score": 0.94,
        "gap_hours": 3.2
    }
