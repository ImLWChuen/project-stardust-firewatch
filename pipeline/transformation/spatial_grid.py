"""Assign point fire observations to discrete equal-angle spatial grid cells.

Methodology Note:
Although high-level architecture docs refer to equal-area gridding, the repository
configuration (`grid_resolution_deg: 0.01` in `config/harmonization.yaml`) and contract
(`grid_size_deg: 0.01` in `contracts/schemas/fire-cell-day.schema.json`) define a
fixed-degree (equal-angle) WGS84 grid. Longitudinal cell width scales with cos(latitude).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from science.harmonization.spatial_normalization import (
    assign_grid_cell,
    format_cell_id,
    validate_grid_size,
)


def grid_observations(
    df: pd.DataFrame,
    *,
    grid_size: float | None = None,
    drop_invalid_coords: bool = False,
) -> pd.DataFrame:
    """Assign each fire observation to a deterministic spatial grid cell.

    Adds `cell_id`, `cell_lat`, `cell_lon`, and `grid_size_deg` columns.

    Args:
        df: Fire observation DataFrame containing `latitude` and `longitude`.
        grid_size: Grid cell size in decimal degrees (defaults to configured 0.01).
        drop_invalid_coords: If True, drop rows with missing or out-of-range
            coordinates instead of raising ValueError.

    Returns:
        DataFrame with `cell_id`, `cell_lat`, `cell_lon`, and `grid_size_deg` columns.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    res = validate_grid_size(grid_size)

    if df.empty and ("latitude" not in df.columns or "longitude" not in df.columns):
        empty = df.copy()
        if "latitude" not in empty.columns:
            empty["latitude"] = pd.Series(dtype="float64")
        if "longitude" not in empty.columns:
            empty["longitude"] = pd.Series(dtype="float64")
        empty["cell_id"] = pd.Series(dtype="object")
        empty["cell_lat"] = pd.Series(dtype="float64")
        empty["cell_lon"] = pd.Series(dtype="float64")
        empty["grid_size_deg"] = pd.Series(dtype="float64")
        return empty

    if "latitude" not in df.columns or "longitude" not in df.columns:
        raise ValueError(
            "Input DataFrame must contain 'latitude' and 'longitude' columns."
        )

    if df.empty:
        empty = df.copy()
        empty["cell_id"] = pd.Series(dtype="object", index=empty.index)
        empty["cell_lat"] = pd.Series(dtype="float64", index=empty.index)
        empty["cell_lon"] = pd.Series(dtype="float64", index=empty.index)
        empty["grid_size_deg"] = pd.Series(dtype="float64", index=empty.index)
        return empty

    work = df.copy()
    lat_num = pd.to_numeric(work["latitude"], errors="coerce")
    lon_num = pd.to_numeric(work["longitude"], errors="coerce")

    valid_mask = (
        lat_num.notna()
        & lon_num.notna()
        & np.isfinite(lat_num)
        & np.isfinite(lon_num)
        & (lat_num >= -90.0)
        & (lat_num <= 90.0)
        & (lon_num >= -180.0)
        & (lon_num <= 180.0)
    )

    if not valid_mask.all():
        if not drop_invalid_coords:
            bad_count = int((~valid_mask).sum())
            raise ValueError(
                f"Cannot assign spatial grid cells: {bad_count} row(s) have missing or "
                "out-of-range coordinates."
            )
        work = work.loc[valid_mask].copy().reset_index(drop=True)
        lat_num = lat_num.loc[valid_mask].reset_index(drop=True)
        lon_num = lon_num.loc[valid_mask].reset_index(drop=True)

    if work.empty:
        work["cell_id"] = pd.Series(dtype="object", index=work.index)
        work["cell_lat"] = pd.Series(dtype="float64", index=work.index)
        work["cell_lon"] = pd.Series(dtype="float64", index=work.index)
        work["grid_size_deg"] = pd.Series(dtype="float64", index=work.index)
        return work

    work["latitude"] = lat_num.astype("float64")
    work["longitude"] = lon_num.astype("float64")

    cell_lats: list[float] = []
    cell_lons: list[float] = []
    cell_ids: list[str] = []

    for lat_val, lon_val in zip(work["latitude"].tolist(), work["longitude"].tolist()):
        c_lat, c_lon = assign_grid_cell(lat_val, lon_val, grid_size=res)
        c_id = format_cell_id(c_lat, c_lon, grid_size=res)
        cell_lats.append(c_lat)
        cell_lons.append(c_lon)
        cell_ids.append(c_id)

    work["cell_id"] = pd.Series(cell_ids, index=work.index, dtype="object")
    work["cell_lat"] = pd.Series(cell_lats, index=work.index, dtype="float64")
    work["cell_lon"] = pd.Series(cell_lons, index=work.index, dtype="float64")
    work["grid_size_deg"] = pd.Series(res, index=work.index, dtype="float64")
    return work
