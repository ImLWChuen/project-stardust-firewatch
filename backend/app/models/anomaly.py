from dataclasses import dataclass

@dataclass
class AnomalyModel:
    id: str
    entity_id: str
    date: str
    observed_activity: float
    climatological_mean: float
    z_score: float
    severity: str
    critical_period_flag: bool
