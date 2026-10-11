"""Spatial gridding and footprint normalization algorithms.

Methodology Note:
The configured 0.01-degree grid is an equal-angle geographic (WGS84 latitude/longitude)
grid, NOT a true equal-area projection grid. Cell longitudinal width varies with
cos(latitude) (~1.11 km x 1.11 km at the equator, narrowing toward the poles).
"""
from __future__ import annotations

import math
from decimal import Decimal

import numpy as np

from science.harmonization.config import get_configured_grid_resolution


def validate_grid_size(grid_size: float | None = None) -> float:
    """Validate and return spatial grid resolution in degrees."""
    resolved = get_configured_grid_resolution() if grid_size is None else grid_size
    if isinstance(resolved, bool) or not isinstance(resolved, (int, float, np.number)):
        raise TypeError("grid_size must be a positive number.")
    val = float(resolved)
    if not math.isfinite(val) or val <= 0.0 or val > 90.0:
        raise ValueError(f"grid_size must be in (0.0, 90.0], got {resolved!r}.")
    return val


def grid_precision_decimals(grid_size: float) -> int:
    """Determine decimal places needed to represent grid cell centers cleanly."""
    dec = Decimal(str(grid_size)).normalize()
    exponent = dec.as_tuple().exponent
    if isinstance(exponent, int) and exponent < 0:
        return max(2, -exponent)
    return 2


def _validate_coord_pair(lat: float, lon: float) -> tuple[float, float]:
    """Validate a single (latitude, longitude) coordinate pair."""
    if isinstance(lat, bool) or not isinstance(lat, (int, float, np.number)):
        raise TypeError(f"latitude must be numeric, got {type(lat).__name__}.")
    if isinstance(lon, bool) or not isinstance(lon, (int, float, np.number)):
        raise TypeError(f"longitude must be numeric, got {type(lon).__name__}.")

    lat_f = float(lat)
    lon_f = float(lon)
    if not math.isfinite(lat_f) or not math.isfinite(lon_f):
        raise ValueError(f"Coordinates must be finite numbers, got ({lat!r}, {lon!r}).")
    if lat_f < -90.0 or lat_f > 90.0:
        raise ValueError(f"latitude {lat_f} is out of valid range [-90.0, 90.0].")
    if lon_f < -180.0 or lon_f > 180.0:
        raise ValueError(f"longitude {lon_f} is out of valid range [-180.0, 180.0].")
    return lat_f, lon_f


def assign_grid_cell(
    lat: float,
    lon: float,
    grid_size: float | None = None,
) -> tuple[float, float]:
    """Assign latitude and longitude to a standard equal-angle grid cell center.

    Args:
        lat: Latitude in decimal degrees [-90.0, 90.0].
        lon: Longitude in decimal degrees [-180.0, 180.0].
        grid_size: Grid resolution in degrees (defaults to configured 0.01 deg).

    Returns:
        Tuple of (cell_lat, cell_lon) in decimal degrees.
    """
    lat_f, lon_f = _validate_coord_pair(lat, lon)
    res = validate_grid_size(grid_size)
    decimals = grid_precision_decimals(res)

    # Round ratio to 9 decimals first to avoid IEEE 754 binary division jitter on boundaries
    lat_steps = round(lat_f / res, 9)
    lon_steps = round(lon_f / res, 9)

    cell_lat = round(float(np.round(lat_steps)) * res, decimals)
    cell_lon = round(float(np.round(lon_steps)) * res, decimals)

    cell_lat = max(-90.0, min(90.0, cell_lat))
    cell_lon = max(-180.0, min(180.0, cell_lon))

    if cell_lat == 0.0:
        cell_lat = 0.0
    if cell_lon == 0.0:
        cell_lon = 0.0

    return (float(cell_lat), float(cell_lon))


def format_cell_id(
    cell_lat: float,
    cell_lon: float,
    grid_size: float | None = None,
) -> str:
    """Format a deterministic string cell_id from grid cell center coordinates."""
    lat_f, lon_f = _validate_coord_pair(cell_lat, cell_lon)
    res = validate_grid_size(grid_size)
    decimals = grid_precision_decimals(res)

    clean_lat = 0.0 if round(lat_f, decimals) == 0.0 else round(lat_f, decimals)
    clean_lon = 0.0 if round(lon_f, decimals) == 0.0 else round(lon_f, decimals)
    return f"cell_{clean_lat:.{decimals}f}_{clean_lon:.{decimals}f}"
