"""Spatial gridding and footprint normalization algorithms."""
import numpy as np

def assign_grid_cell(lat: float, lon: float, grid_size: float = 0.01) -> tuple[float, float]:
    """Assign latitude and longitude to a standard equal-angle grid cell center."""
    cell_lat = np.round(lat / grid_size) * grid_size
    cell_lon = np.round(lon / grid_size) * grid_size
    return (float(cell_lat), float(cell_lon))
