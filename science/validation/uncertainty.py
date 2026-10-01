"""Uncertainty and confidence interval estimation."""

def estimate_confidence_interval(estimate: float, stderr: float, z: float = 1.96):
    return (estimate - z * stderr, estimate + z * stderr)
