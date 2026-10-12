from pydantic import BaseModel

class AnomalySummaryResponse(BaseModel):
    """Response schema for anomaly summary data for an area of interest."""

    aoi_id: str
    active_anomalies_count: int
    severity: str
