from science.harmonization.sensor_calibration import SensorCalibrationModel

def test_sensor_calibration():
    """Verify the sensor calibration model applies its linear coefficients correctly."""
    model = SensorCalibrationModel(alpha=1.2, beta=0.5)
    assert model.predict(10.0) == 12.5
