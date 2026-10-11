"""Temporal deduplication for co-incident satellite overpasses.

Policy Note:
By default (`group_by_sensor=True`), deduplication groups observations by
`(cell_id, sensor)` so redundant detections from the same instrument family within
the configured 20-minute window are collapsed while cross-sensor detections
(MODIS vs. VIIRS) are preserved for downstream sensor counts and overlap calibration.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from pipeline.preprocessing.normalize_fields import (
    _is_missing,
    _parse_row_timestamp,
    normalize_satellite_name,
    normalize_sensor_name,
)
from science.harmonization.config import get_configured_dedup_window_minutes


def validate_window_minutes(window_minutes: float | None = None) -> float:
    """Validate and return the temporal deduplication window in minutes."""
    resolved = (
        get_configured_dedup_window_minutes()
        if window_minutes is None
        else window_minutes
    )
    if isinstance(resolved, bool) or not isinstance(resolved, (int, float, np.number)):
        raise TypeError("window_minutes must be a non-negative number.")
    val = float(resolved)
    if not math.isfinite(val) or val < 0.0:
        raise ValueError(f"window_minutes must be >= 0.0, got {resolved!r}.")
    return val


def _resolve_row_timestamps(df: pd.DataFrame) -> list[pd.Timestamp]:
    """Extract or parse a UTC pd.Timestamp for every row in df."""
    n_rows = len(df)
    has_dt = "acq_datetime" in df.columns
    has_date = "acq_date" in df.columns
    has_fallback_date = "date" in df.columns
    has_time = "acq_time" in df.columns

    if not has_dt and not has_date and not has_fallback_date:
        raise ValueError(
            "DataFrame must contain 'acq_datetime', 'acq_date', or 'date' for temporal deduplication."
        )

    raw_dts = df["acq_datetime"].tolist() if has_dt else [None] * n_rows
    raw_dates = (
        df["acq_date"].tolist()
        if has_date
        else (df["date"].tolist() if has_fallback_date else [None] * n_rows)
    )
    raw_times = df["acq_time"].tolist() if has_time else ["0000"] * n_rows

    timestamps: list[pd.Timestamp] = []
    for i in range(n_rows):
        ts, _, _ = _parse_row_timestamp(raw_dates[i], raw_times[i], raw_dts[i])
        if pd.isna(ts):
            raise ValueError(
                f"Row {i} has a missing or unparseable acquisition timestamp."
            )
        timestamps.append(ts)
    return timestamps


def _resolve_row_sensors(df: pd.DataFrame) -> list[str]:
    """Resolve canonical sensor key per row ('MODIS', 'VIIRS', or '' if absent)."""
    n_rows = len(df)
    if "sensor" in df.columns:
        raw_vals = df["sensor"].tolist()
    elif "instrument" in df.columns:
        raw_vals = df["instrument"].tolist()
    elif "satellite" in df.columns:
        sats = df["satellite"].tolist()
        return [normalize_satellite_name(s)[1] or "" for s in sats]
    else:
        return [""] * n_rows

    resolved: list[str] = []
    for val in raw_vals:
        if _is_missing(val):
            resolved.append("")
        else:
            norm = normalize_sensor_name(val)
            resolved.append(norm if norm is not None else str(val).strip().upper())
    return resolved


def deduplicate_temporal_window(
    df: pd.DataFrame,
    window_minutes: float | None = None,
    *,
    group_by_sensor: bool = True,
) -> pd.DataFrame:
    """Deduplicate detections within the same grid cell (and sensor) within a time window.

    Detections separated by `<= window_minutes` (default: configured 20 minutes)
    within the same group are collapsed into a single representative observation,
    whereas detections separated by `> window_minutes` are retained as distinct events.

    Args:
        df: DataFrame containing at least `cell_id` and timestamp/date fields.
        window_minutes: Deduplication window in minutes (defaults to configured 20).
        group_by_sensor: If True (default), group by `(cell_id, sensor)` so
            cross-sensor detections are not discarded. If False, group by `cell_id` only.

    Returns:
        Deduplicated DataFrame in deterministic chronological order.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    win_min = validate_window_minutes(window_minutes)

    if df.empty:
        return df.copy()

    if "cell_id" not in df.columns:
        raise ValueError(
            "DataFrame must contain 'cell_id' column for temporal deduplication."
        )

    cell_ids = df["cell_id"].tolist()
    if any(_is_missing(cid) for cid in cell_ids):
        raise ValueError("DataFrame contains missing 'cell_id' values.")

    timestamps = _resolve_row_timestamps(df)
    sensor_labels = _resolve_row_sensors(df)

    if "frp" in df.columns:
        frp_series = pd.to_numeric(df["frp"], errors="coerce").fillna(-1.0)
        frp_vals = [float(v) for v in frp_series.tolist()]
    else:
        frp_vals = [0.0] * len(df)

    groups: dict[tuple[str, str], list[int]] = {}
    for idx in range(len(df)):
        key = (
            str(cell_ids[idx]),
            sensor_labels[idx] if group_by_sensor else "",
        )
        groups.setdefault(key, []).append(idx)

    kept_indices: list[int] = []
    for indices in groups.values():
        # Deterministic ordering: earliest timestamp first; ties broken by highest FRP, then original index
        sorted_indices = sorted(
            indices,
            key=lambda i: (timestamps[i], -frp_vals[i], i),
        )
        anchor_ts: pd.Timestamp | None = None
        for i in sorted_indices:
            curr_ts = timestamps[i]
            if anchor_ts is None:
                kept_indices.append(i)
                anchor_ts = curr_ts
            else:
                delta_minutes = (curr_ts - anchor_ts).total_seconds() / 60.0
                if delta_minutes > win_min:
                    kept_indices.append(i)
                    anchor_ts = curr_ts

    # Sort surviving rows deterministically by timestamp, cell_id, sensor, and original index
    kept_indices.sort(
        key=lambda i: (timestamps[i], str(cell_ids[i]), sensor_labels[i], i)
    )

    result: Any = df.iloc[kept_indices].copy().reset_index(drop=True)
    return result
