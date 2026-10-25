from dataclasses import dataclass

@dataclass
class CalibrationModel:
    """Domain model representing a sensor calibration model version."""

    model_id: str
    version: str
    alpha: float
    beta: float
