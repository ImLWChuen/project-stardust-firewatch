"""Calculate spatial and temporal satellite observation coverage frequency."""
from typing import Dict, Any, List

def compute_daily_coverage(overpass_times: List[str], cell_area_km2: float) -> Dict[str, Any]:
    """Compute day/night overpass count and coverage metrics."""
    count = len(overpass_times)
    coverage_ratio = min(1.0, count / 4.0)
    return {
        "overpass_count": count,
        "coverage_ratio": coverage_ratio,
        "is_adequately_covered": count >= 2
    }
