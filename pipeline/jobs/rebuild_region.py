"""Rebuild historical or near-real-time fire observations and FireCellDay records for a region."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_type
from datetime import datetime
from pathlib import Path
from typing import Any

from pipeline.jobs.daily_update import (
    build_arg_parser,
    run_firms_pipeline,
)
from pipeline.jobs.daily_update import (
    main as _daily_main,
)


def rebuild_region(
    region_id: str | None = None,
    *,
    bbox: str | Sequence[int | float] | None = None,
    start_date: str | date_type | datetime | None = None,
    end_date: str | date_type | datetime | None = None,
    mode: str = "sp",
    sensor: str = "all",
    raw_dir: str | Path | None = None,
    interim_dir: str | Path | None = None,
    processed_dir: str | Path | None = None,
    save_raw_chunks: bool = False,
) -> dict[str, Any]:
    """Run the end-to-end FIRMS ingestion and FireCellDay pipeline for a region."""
    return run_firms_pipeline(
        region=region_id,
        bbox=bbox,
        start_date=start_date,
        end_date=end_date,
        mode=mode,
        sensor=sensor,
        raw_dir=raw_dir,
        interim_dir=interim_dir,
        processed_dir=processed_dir,
        save_raw_chunks=save_raw_chunks,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for rebuilding a region's FIRMS dataset."""
    return _daily_main(argv, prog="python -m pipeline.jobs.rebuild_region")


__all__ = ["build_arg_parser", "main", "rebuild_region", "run_firms_pipeline"]


if __name__ == "__main__":
    raise SystemExit(main())
