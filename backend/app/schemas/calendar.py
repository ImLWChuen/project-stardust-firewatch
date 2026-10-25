from pydantic import BaseModel

class BurningCalendarResponse(BaseModel):
    """Response schema for the burning calendar of an area of interest."""

    aoi_id: str
    year: int
    status: str
    peak_window_start: str
    peak_window_end: str
    daily_risk_levels: list[dict]
