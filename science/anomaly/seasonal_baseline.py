"""Rolling seasonal baseline calculation."""

def get_seasonal_baseline(day_of_year: int, climatology_map: dict) -> float:
    """Look up the seasonal baseline value for the given day of year, defaulting to 0.0."""
    return climatology_map.get(day_of_year, 0.0)
