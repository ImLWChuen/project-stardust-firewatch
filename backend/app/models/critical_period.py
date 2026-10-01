from dataclasses import dataclass

@dataclass
class CriticalPeriodModel:
    id: str
    aoi_id: str
    period_name: str
    start_date: str
    end_date: str
    risk_tier: str
    active: bool
