"""Build the primary fire_cell_day analytical dataset."""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from pipeline.preprocessing.normalize_fields import normalize_fields
from pipeline.preprocessing.quality_control import QCConfig, filter_invalid_rows
from pipeline.transformation.aggregate_daily import (
    FIRE_CELL_DAY_COLUMNS,
    _empty_fire_cell_day_dataframe,
    aggregate_daily,
)
from pipeline.transformation.spatial_grid import grid_observations
from pipeline.transformation.temporal_dedup import deduplicate_observations


def _needs_field_normalization(df: pd.DataFrame) -> bool:
    """Return True if raw FIRMS columns need canonical normalization before gridding."""
    if df.attrs.get("normalized") is True:
        return False
    # If bright_ti4 is present or acq_datetime is missing while acq_date+acq_time exist
    if "bright_ti4" in df.columns:
        return True
    if "acq_datetime" not in df.columns and "acq_date" in df.columns and "acq_time" in df.columns:
        return True
    return bool("sensor" not in df.columns and "satellite" in df.columns)


def build_fire_cell_day(
    df: pd.DataFrame | Sequence[pd.DataFrame] | None = None,
    *,
    grid_size: float | None = None,
    dedup_window_minutes: float | None = None,
    deduplicate: bool = True,
    group_by_sensor: bool = True,
    run_qc: bool = False,
    qc_config: QCConfig | None = None,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """Build the canonical `FireCellDay` dataset from fire observations.

    Executes:
    1. Optional normalization / quality control (`run_qc=True`).
    2. Spatial grid cell assignment (`grid_observations`).
    3. Temporal deduplication within configured window (`deduplicate_observations`).
    4. Daily cell-level aggregation (`aggregate_daily`).

    Args:
        df: Input DataFrame or sequence of DataFrames (returns empty FireCellDay if None).
        grid_size: Spatial grid resolution in degrees (defaults to configured 0.01).
        dedup_window_minutes: Temporal deduplication window in minutes (defaults to configured 20).
        deduplicate: Whether to run temporal deduplication before daily aggregation.
        group_by_sensor: Whether temporal deduplication preserves distinct sensors.
        run_qc: If True, run full Step 3 quality control filtering before gridding.
        qc_config: Optional QCConfig when `run_qc=True`.
        output_path: Optional path to write the resulting CSV dataset.

    Returns:
        DataFrame matching `contracts/schemas/fire-cell-day.schema.json`.
    """
    if df is None:
        result = _empty_fire_cell_day_dataframe()
    elif isinstance(df, pd.DataFrame):
        work = df.copy()
        work.attrs.update(df.attrs)
        result = _process_dataframe(
            work,
            grid_size=grid_size,
            dedup_window_minutes=dedup_window_minutes,
            deduplicate=deduplicate,
            group_by_sensor=group_by_sensor,
            run_qc=run_qc,
            qc_config=qc_config,
        )
    elif isinstance(df, Sequence) and not isinstance(df, (str, bytes)):
        frames: list[pd.DataFrame] = []
        for item in df:
            if not isinstance(item, pd.DataFrame):
                raise TypeError("All elements of df sequence must be pandas DataFrames.")
            if not item.empty:
                frames.append(
                    normalize_fields(item) if _needs_field_normalization(item) else item.copy()
                )
        if not frames:
            result = _empty_fire_cell_day_dataframe()
        else:
            combined = pd.concat(frames, ignore_index=True)
            result = _process_dataframe(
                combined,
                grid_size=grid_size,
                dedup_window_minutes=dedup_window_minutes,
                deduplicate=deduplicate,
                group_by_sensor=group_by_sensor,
                run_qc=run_qc,
                qc_config=qc_config,
            )
    else:
        raise TypeError("df must be a pandas DataFrame, a sequence of DataFrames, or None.")

    if output_path is not None:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(out_file, index=False)

    return result


def _process_dataframe(
    work: pd.DataFrame,
    *,
    grid_size: float | None,
    dedup_window_minutes: float | None,
    deduplicate: bool,
    group_by_sensor: bool,
    run_qc: bool,
    qc_config: QCConfig | None,
) -> pd.DataFrame:
    if work.empty:
        return _empty_fire_cell_day_dataframe()

    if run_qc:
        work = filter_invalid_rows(work, config=qc_config)
        if work.empty:
            return _empty_fire_cell_day_dataframe()
    elif _needs_field_normalization(work):
        work = normalize_fields(work)

    gridded = grid_observations(work, grid_size=grid_size)
    if deduplicate:
        gridded = deduplicate_observations(
            gridded,
            window_minutes=dedup_window_minutes,
            group_by_sensor=group_by_sensor,
            grid_size=grid_size,
        )
    return aggregate_daily(gridded, grid_size=grid_size)


__all__ = ["FIRE_CELL_DAY_COLUMNS", "build_fire_cell_day"]


if __name__ == "__main__":
    build_fire_cell_day()
