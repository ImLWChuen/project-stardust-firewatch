"""Filter redundant detections within coincident satellite orbits."""
from __future__ import annotations

import pandas as pd

from pipeline.transformation.spatial_grid import grid_observations
from science.harmonization.temporal_normalization import (
    deduplicate_temporal_window,
    validate_window_minutes,
)


def deduplicate_observations(
    df: pd.DataFrame,
    *,
    window_minutes: float | None = None,
    group_by_sensor: bool = True,
    grid_size: float | None = None,
) -> pd.DataFrame:
    """Deduplicate observations within the configured temporal window per grid cell and sensor.

    If `cell_id` is not yet present on `df` and `latitude`/`longitude` are available,
    spatial grid cells are assigned first.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    validate_window_minutes(window_minutes)

    if df.empty:
        return df.copy()

    work = df
    if "cell_id" not in work.columns:
        if "latitude" in work.columns and "longitude" in work.columns:
            work = grid_observations(work, grid_size=grid_size)
        else:
            raise ValueError(
                "DataFrame must contain 'cell_id' or ('latitude', 'longitude') columns."
            )

    return deduplicate_temporal_window(
        work,
        window_minutes=window_minutes,
        group_by_sensor=group_by_sensor,
    )
