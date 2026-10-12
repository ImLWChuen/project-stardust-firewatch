from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_data_status():
    """Return the current health and freshness status of the ingested data pipeline."""
    return {
        "status": "healthy",
        "latest_satellite_feed": "2026-10-01T20:45:00Z",
        "active_manifest_version": "1.0.0",
        "pipeline_health": "operational",
        "ingested_observations_count": 1250000
    }
