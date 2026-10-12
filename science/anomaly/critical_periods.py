"""Identification of critical agricultural burning alert periods."""

def identify_critical_periods(anomaly_series: list[float], threshold: float = 2.0) -> list[int]:
    """Return the indices of an anomaly series where values meet or exceed the critical threshold."""
    return [i for i, val in enumerate(anomaly_series) if val >= threshold]
