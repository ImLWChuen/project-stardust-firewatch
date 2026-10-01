from dataclasses import dataclass

@dataclass
class CalibrationModel:
    model_id: str
    version: str
    alpha: float
    beta: float
