"""Model sensor minimum fire radiative power (FRP) detectability thresholds."""

def calculate_detectability_threshold(instrument: str, scan_angle_deg: float = 0.0) -> float:
    """Return minimum estimated FRP (MW) detectable by sensor at given scan angle."""
    base_thresh = 10.0 if instrument.upper() == "MODIS" else 1.5
    # Pixel expansion distortion penalty
    angle_factor = 1.0 + 0.5 * (scan_angle_deg / 55.0) ** 2
    return base_thresh * angle_factor
