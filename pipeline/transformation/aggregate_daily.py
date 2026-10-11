"""Aggregate gridded fire observations into daily cell summaries (FireCellDay)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline.preprocessing.normalize_fields import (
    _is_missing,
    normalize_acq_date,
    normalize_satellite_name,
    normalize_sensor_name,
)
from pipeline.transformation.spatial_grid import grid_observations
from science.harmonization.spatial_normalization import validate_grid_size

FIRE_CELL_DAY_COLUMNS: tuple[str, ...] = (
    "cell_id",
    "date",
    "cell_lat",
    "cell_lon",
    "grid_size_deg",
    "raw_count",
    "raw_frp_sum",
    "raw_frp_mean",
    "modis_count",
    "viirs_count",
    "sensors_present",
)


def _empty_fire_cell_day_dataframe() -> pd.DataFrame:
    """Return an empty DataFrame conforming to the FireCellDay JSON schema."""
    return pd.DataFrame(
        {
            "cell_id": pd.Series(dtype="object"),
            "date": pd.Series(dtype="object"),
            "cell_lat": pd.Series(dtype="float64"),
            "cell_lon": pd.Series(dtype="float64"),
            "grid_size_deg": pd.Series(dtype="float64"),
            "raw_count": pd.Series(dtype="int64"),
            "raw_frp_sum": pd.Series(dtype="float64"),
            "raw_frp_mean": pd.Series(dtype="float64"),
            "modis_count": pd.Series(dtype="int64"),
            "viirs_count": pd.Series(dtype="int64"),
            "sensors_present": pd.Series(dtype="object"),
        }
    )


def _resolve_observation_dates(df: pd.DataFrame) -> list[str]:
    """Resolve UTC YYYY-MM-DD date string for every row in df."""
    n_rows = len(df)
    has_date = "date" in df.columns
    has_acq_date = "acq_date" in df.columns
    has_acq_dt = "acq_datetime" in df.columns

    if not has_date and not has_acq_date and not has_acq_dt:
        raise ValueError(
            "Input DataFrame must contain 'date', 'acq_date', or 'acq_datetime' column."
        )

    raw_dates = df["date"].tolist() if has_date else [None] * n_rows
    raw_acq_dates = df["acq_date"].tolist() if has_acq_date else [None] * n_rows
    raw_acq_dts = df["acq_datetime"].tolist() if has_acq_dt else [None] * n_rows

    dates: list[str] = []
    for i in range(n_rows):
        d_str: str | None = None
        if not _is_missing(raw_acq_dts[i]):
            try:
                ts = pd.to_datetime(raw_acq_dts[i], utc=True, errors="raise")
                if not pd.isna(ts):
                    d_str = ts.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                d_str = None
        if d_str is None and not _is_missing(raw_acq_dates[i]):
            d_str = normalize_acq_date(raw_acq_dates[i])
        if d_str is None and not _is_missing(raw_dates[i]):
            d_str = normalize_acq_date(raw_dates[i])

        if d_str is None:
            raise ValueError(f"Row {i} has a missing or invalid observation date.")
        dates.append(d_str)
    return dates


def _resolve_sensor_for_aggregation(df: pd.DataFrame) -> list[str | None]:
    """Resolve canonical sensor ('MODIS', 'VIIRS', or None) for each row."""
    n_rows = len(df)
    has_sensor = "sensor" in df.columns
    has_inst = "instrument" in df.columns
    has_sat = "satellite" in df.columns

    raw_sensors = df["sensor"].tolist() if has_sensor else [None] * n_rows
    raw_insts = df["instrument"].tolist() if has_inst else [None] * n_rows
    raw_sats = df["satellite"].tolist() if has_sat else [None] * n_rows

    resolved: list[str | None] = []
    for i in range(n_rows):
        s_val = normalize_sensor_name(raw_sensors[i])
        if s_val is None:
            s_val = normalize_sensor_name(raw_insts[i])
        if s_val is None and not _is_missing(raw_sats[i]):
            _, s_val = normalize_satellite_name(raw_sats[i])
        resolved.append(s_val)
    return resolved


def aggregate_daily(
    df: pd.DataFrame,
    *,
    grid_size: float | None = None,
) -> pd.DataFrame:
    """Aggregate point fire observations into daily spatial grid cell records.

    Produces the canonical `FireCellDay` structure defined by
    `contracts/schemas/fire-cell-day.schema.json`.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    res = validate_grid_size(grid_size)

    if df.empty:
        return _empty_fire_cell_day_dataframe()

    work = df.copy()
    if (
        "cell_id" not in work.columns
        or "cell_lat" not in work.columns
        or "cell_lon" not in work.columns
    ):
        if "latitude" in work.columns and "longitude" in work.columns:
            work = grid_observations(work, grid_size=res)
        else:
            raise ValueError(
                "Input DataFrame must contain ('cell_id', 'cell_lat', 'cell_lon') "
                "or ('latitude', 'longitude') columns."
            )

    if "frp" not in work.columns:
        raise ValueError("Input DataFrame must contain 'frp' column for aggregation.")

    frp_series = pd.to_numeric(work["frp"], errors="coerce")
    if frp_series.isna().any() or not np.isfinite(frp_series).all() or (frp_series < 0.0).any():
        raise ValueError(
            "Input DataFrame contains missing, non-numeric, or negative 'frp' values."
        )

    dates = _resolve_observation_dates(work)
    sensors = _resolve_sensor_for_aggregation(work)
    cell_ids = work["cell_id"].tolist()
    cell_lats = pd.to_numeric(work["cell_lat"], errors="coerce").tolist()
    cell_lons = pd.to_numeric(work["cell_lon"], errors="coerce").tolist()
    grid_sizes = (
        pd.to_numeric(work["grid_size_deg"], errors="coerce").tolist()
        if "grid_size_deg" in work.columns
        else [res] * len(work)
    )
    frp_vals = [float(v) for v in frp_series.tolist()]

    # Group by (date, cell_id)
    grouped: dict[tuple[str, str], list[int]] = {}
    for idx in range(len(work)):
        cid = cell_ids[idx]
        if _is_missing(cid):
            raise ValueError(f"Row {idx} has a missing 'cell_id'.")
        key = (dates[idx], str(cid))
        grouped.setdefault(key, []).append(idx)

    records: list[dict[str, object]] = []
    for (date_str, cid_str), indices in sorted(grouped.items(), key=lambda item: item[0]):
        first_idx = indices[0]
        c_lat = float(cell_lats[first_idx])
        c_lon = float(cell_lons[first_idx])
        g_size = float(grid_sizes[first_idx]) if not _is_missing(grid_sizes[first_idx]) else res

        group_frps = [frp_vals[i] for i in indices]
        raw_count = len(indices)
        raw_frp_sum = float(sum(group_frps))
        raw_frp_mean = float(raw_frp_sum / raw_count)

        modis_count = sum(1 for i in indices if sensors[i] == "MODIS")
        viirs_count = sum(1 for i in indices if sensors[i] == "VIIRS")
        present_set = {sensors[i] for i in indices if sensors[i] is not None}
        sensors_present = sorted(present_set)

        records.append(
            {
                "cell_id": cid_str,
                "date": date_str,
                "cell_lat": c_lat,
                "cell_lon": c_lon,
                "grid_size_deg": g_size,
                "raw_count": raw_count,
                "raw_frp_sum": raw_frp_sum,
                "raw_frp_mean": raw_frp_mean,
                "modis_count": modis_count,
                "viirs_count": viirs_count,
                "sensors_present": sensors_present,
            }
        )

    out = pd.DataFrame(records)
    return out.astype(
        {
            "cell_id": "object",
            "date": "object",
            "cell_lat": "float64",
            "cell_lon": "float64",
            "grid_size_deg": "float64",
            "raw_count": "int64",
            "raw_frp_sum": "float64",
            "raw_frp_mean": "float64",
            "modis_count": "int64",
            "viirs_count": "int64",
            "sensors_present": "object",
        }
    )
