"""Z-score and percentile anomaly ranking."""

def compute_anomaly_zscore(current_val: float, mean: float, std: float) -> float:
    """Compute the z-score of a current value against a historical mean and standard deviation."""
    if std <= 1e-6:
        return 0.0
    return (current_val - mean) / std
