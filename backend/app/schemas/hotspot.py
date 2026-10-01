from pydantic import BaseModel

class HotspotResponse(BaseModel):
    latitude: float
    longitude: float
    frp: float
    acq_date: str

class HotspotListResponse(BaseModel):
    count: int
    hotspots: list[HotspotResponse]
