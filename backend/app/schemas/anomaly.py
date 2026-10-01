from pydantic import BaseModel

class AnomalySummaryResponse(BaseModel):
    aoi_id: str
    active_anomalies_count: int
    severity: str
