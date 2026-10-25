from pydantic import BaseModel

class HotspotResponse(BaseModel):
    """Response schema for a single fire hotspot."""

    latitude: float
    longitude: float
    frp: float
    acq_date: str

class HotspotListResponse(BaseModel):
    """Response schema for a list of fire hotspots."""

    count: int
    hotspots: list[HotspotResponse]
