"""Regression models calibrating MODIS to VIIRS FRP and hotspot sensitivity."""

class SensorCalibrationModel:
    """Linear regression model calibrating MODIS FRP values to the VIIRS scale."""

    def __init__(self, alpha: float = 1.0, beta: float = 0.0):
        """Initialize the model with the given slope (alpha) and intercept (beta)."""
        self.alpha = alpha
        self.beta = beta

    def predict(self, modis_frp: float) -> float:
        """Predict the calibrated FRP value for a given MODIS FRP input."""
        return self.alpha * modis_frp + self.beta
