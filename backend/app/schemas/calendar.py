from pydantic import BaseModel

class BurningCalendarResponse(BaseModel):
    aoi_id: str
    year: int
    status: str
    peak_window_start: str
    peak_window_end: str
    daily_risk_levels: list[dict]
