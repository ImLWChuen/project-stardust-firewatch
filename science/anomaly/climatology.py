"""Calculation of historical seasonal climatology per grid cell."""
import numpy as np

def compute_climatological_mean(historical_series: list[float]) -> float:
    """Compute the historical climatological mean of a series, returning 0.0 for an empty series."""
    return float(np.mean(historical_series)) if historical_series else 0.0
