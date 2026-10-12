"""Statistical helpers (percentiles, rolling windows)."""
import numpy as np

def rolling_percentile(data: list[float], percentile: float = 90.0) -> float:
    """Compute the given percentile of a data series, returning 0.0 for empty input."""
    return float(np.percentile(data, percentile)) if data else 0.0
