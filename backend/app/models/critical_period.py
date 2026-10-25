from dataclasses import dataclass

@dataclass
class CriticalPeriodModel:
    """Domain model representing a critical burning period for an area of interest."""

    id: str
    aoi_id: str
    period_name: str
    start_date: str
    end_date: str
    risk_tier: str
    active: bool
