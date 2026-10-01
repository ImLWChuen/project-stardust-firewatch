"""Rolling seasonal baseline calculation."""

def get_seasonal_baseline(day_of_year: int, climatology_map: dict) -> float:
    return climatology_map.get(day_of_year, 0.0)
