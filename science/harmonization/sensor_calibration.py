"""Regression models calibrating MODIS to VIIRS FRP and hotspot sensitivity."""

class SensorCalibrationModel:
    def __init__(self, alpha: float = 1.0, beta: float = 0.0):
        self.alpha = alpha
        self.beta = beta

    def predict(self, modis_frp: float) -> float:
        return self.alpha * modis_frp + self.beta
