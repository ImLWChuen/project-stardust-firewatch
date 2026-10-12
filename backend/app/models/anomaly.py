from dataclasses import dataclass

@dataclass
class AnomalyModel:
    """Domain model representing a detected fire activity anomaly."""

    id: str
    entity_id: str
    date: str
    observed_activity: float
    climatological_mean: float
    z_score: float
    severity: str
    critical_period_flag: bool
