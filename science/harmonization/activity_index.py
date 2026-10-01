"""Computation of the composite Harmonized Fire Activity Index."""

def calculate_activity_index(hotspot_count: int, total_frp: float, weight_frp: float = 0.6) -> float:
    """Calculate normalized activity index combining count and energy intensity."""
    return float(hotspot_count * (1 - weight_frp) + total_frp * weight_frp)
