"""Statistical helpers (percentiles, rolling windows)."""
import numpy as np

def rolling_percentile(data: list[float], percentile: float = 90.0) -> float:
    return float(np.percentile(data, percentile)) if data else 0.0
