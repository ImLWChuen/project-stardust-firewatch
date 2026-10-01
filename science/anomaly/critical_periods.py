"""Identification of critical agricultural burning alert periods."""

def identify_critical_periods(anomaly_series: list[float], threshold: float = 2.0) -> list[int]:
    return [i for i, val in enumerate(anomaly_series) if val >= threshold]
