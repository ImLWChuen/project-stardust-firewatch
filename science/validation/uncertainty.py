"""Uncertainty and confidence interval estimation."""

def estimate_confidence_interval(estimate: float, stderr: float, z: float = 1.96):
    """Estimate a confidence interval around a point estimate given its standard error and z-score."""
    return (estimate - z * stderr, estimate + z * stderr)
