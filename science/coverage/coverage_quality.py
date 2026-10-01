"""Compute composite observation quality index for a given grid cell or AOI."""

def compute_quality_index(overpasses: int, cloud_fraction: float) -> float:
    """Score quality from 0.0 (unreliable) to 1.0 (optimal)."""
    base = min(1.0, overpasses / 4.0)
    cloud_penalty = 1.0 - max(0.0, min(1.0, cloud_fraction))
    return float(base * cloud_penalty)
