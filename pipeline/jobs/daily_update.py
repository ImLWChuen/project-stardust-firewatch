"""End-to-end orchestration workflow for NASA FIRMS ingestion, QC, and FireCellDay generation."""
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import date as date_type
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.connectors.firms.client import FIRMSClient, validate_query_date
from pipeline.connectors.firms.downloader import FIRMSDownloader
from pipeline.connectors.firms.parser import parse_firms_csv
from pipeline.ingestion.download_all import download_all
from pipeline.ingestion.download_modis import (
    get_pipeline_data_dirs,
    load_dotenv_if_present,
    resolve_region_bbox,
)
from pipeline.preprocessing.normalize_fields import (
    _empty_canonical_dataframe,
    normalize_fields,
)
from pipeline.preprocessing.quality_control import QCConfig, evaluate_quality_control
from pipeline.transformation.aggregate_daily import aggregate_daily
from pipeline.transformation.spatial_grid import grid_observations
from pipeline.transformation.temporal_dedup import deduplicate_observations
from science.harmonization.config import (
    get_configured_dedup_window_minutes,
    get_configured_grid_resolution,
)
from science.harmonization.spatial_normalization import validate_grid_size
from science.harmonization.temporal_normalization import validate_window_minutes


def _resolve_dir(override: str | Path | None, default_path: Path, name: str) -> Path:
    """Resolve a directory override to a Path, falling back to the default path when unset."""
    if override is None:
        return default_path
    if not isinstance(override, (str, Path)):
        raise TypeError(f"{name} must be a string or Path.")
    text = str(override).strip()
    if not text:
        raise ValueError(f"{name} cannot be an empty string.")
    return Path(text)


def run_firms_pipeline(
    *,
    region: str | None = None,
    bbox: str | Sequence[int | float] | None = None,
    start_date: str | date_type | datetime | None = None,
    end_date: str | date_type | datetime | None = None,
    mode: str = "sp",
    sensor: str = "all",
    raw_dir: str | Path | None = None,
    interim_dir: str | Path | None = None,
    processed_dir: str | Path | None = None,
    regions_config_path: str | Path | None = None,
    harmonization_config_path: str | Path | None = None,
    grid_size: float | None = None,
    dedup_window_minutes: float | None = None,
    group_by_sensor: bool = True,
    qc_config: QCConfig | None = None,
    client: FIRMSClient | None = None,
    downloader: FIRMSDownloader | None = None,
    save_raw_chunks: bool = False,
) -> dict[str, Any]:
    """Execute the end-to-end NASA FIRMS ingestion, QC, gridding, deduplication, and FireCellDay workflow.

    Steps:
    1. Ingest raw MODIS and VIIRS CSV data for the specified region/bbox and date interval.
    2. Preserve raw downloaded CSV files unchanged under `raw_dir`.
    3. Normalize each product using the canonical field normalizer (`source_product` preserved).
    4. Run quality control checks and retain rejection reasons per row.
    5. Combine accepted observations across products while preserving sensor and satellite identity.
    6. Assign the configured 0.01-degree equal-angle spatial grid.
    7. Apply the configured 20-minute temporal deduplication policy (`group_by_sensor=True` by default).
    8. Aggregate accepted detections into daily `FireCellDay` records.
    9. Write normalized, deduplicated, and rejected observation CSVs under `interim_dir`.
    10. Write the final `FireCellDay` CSV under `processed_dir`.
    11. Write reproducible run metadata JSON under `processed_dir`.
    """
    region_slug, validated_bbox = resolve_region_bbox(
        region=region,
        bbox=bbox,
        config_path=regions_config_path,
    )
    if start_date is None or end_date is None:
        raise ValueError(
            "Explicit 'start_date' and 'end_date' (YYYY-MM-DD) are required to run the pipeline."
        )
    start_str = validate_query_date(start_date)
    end_str = validate_query_date(end_date)
    if start_str is None or end_str is None:
        raise ValueError("start_date and end_date are required.")
    if end_str < start_str:
        raise ValueError(
            f"end_date ({end_str}) must be on or after start_date ({start_str})."
        )

    cfg_grid = (
        grid_size
        if grid_size is not None
        else get_configured_grid_resolution(harmonization_config_path)
    )
    resolved_grid_size = validate_grid_size(cfg_grid)

    cfg_win = (
        dedup_window_minutes
        if dedup_window_minutes is not None
        else float(get_configured_dedup_window_minutes(harmonization_config_path))
    )
    resolved_window_minutes = validate_window_minutes(cfg_win)

    data_dirs = get_pipeline_data_dirs()
    base_raw_dir = _resolve_dir(raw_dir, data_dirs["raw"], "raw_dir")
    base_interim_dir = _resolve_dir(interim_dir, data_dirs["interim"], "interim_dir")
    base_processed_dir = _resolve_dir(
        processed_dir, data_dirs["processed"], "processed_dir"
    )

    # 1 & 2. Ingest raw CSVs and preserve them unchanged
    download_results = download_all(
        region=region,
        bbox=bbox,
        start_date=start_str,
        end_date=end_str,
        mode=mode,
        sensor=sensor,
        output_dir=base_raw_dir,
        config_path=regions_config_path,
        client=client,
        downloader=downloader,
        save_raw_chunks=save_raw_chunks,
    )

    valid_frames: list[pd.DataFrame] = []
    rejected_frames: list[pd.DataFrame] = []
    product_summaries: list[dict[str, Any]] = []
    aggregated_rejection_counts: dict[str, int] = {}
    raw_csv_paths: list[str] = []
    products_processed: list[str] = []
    raw_total = 0

    # 3 & 4. Normalize each product and run quality control
    for item in download_results:
        product_code = str(item["source"])
        raw_path = Path(str(item["output_path"]))
        if not raw_path.is_file():
            raise FileNotFoundError(
                f"Expected raw CSV for product {product_code} was not found at {raw_path}"
            )
        raw_csv_paths.append(str(raw_path))
        products_processed.append(product_code)

        raw_text = raw_path.read_text(encoding="utf-8")
        raw_df = parse_firms_csv(raw_text)
        norm_df = normalize_fields(raw_df, source_product=product_code)
        qc_report = evaluate_quality_control(
            norm_df,
            config=qc_config,
            source_product=product_code,
        )

        raw_total += qc_report.total_rows
        for reason, count in qc_report.rejection_counts.items():
            aggregated_rejection_counts[reason] = (
                aggregated_rejection_counts.get(reason, 0) + count
            )

        if not qc_report.valid_df.empty:
            valid_frames.append(qc_report.valid_df)
        if not qc_report.rejected_df.empty:
            rejected_frames.append(qc_report.rejected_df)

        product_summaries.append(
            {
                "source": product_code,
                "raw_output_path": str(raw_path),
                "raw_rows": qc_report.total_rows,
                "valid_rows": qc_report.valid_rows,
                "rejected_rows": qc_report.rejected_rows,
                "rejection_counts": dict(qc_report.rejection_counts),
            }
        )

    # 5. Combine accepted observations across products
    if valid_frames:
        combined_valid_df = pd.concat(valid_frames, ignore_index=True)
        combined_valid_df = combined_valid_df.sort_values(
            by=["acq_datetime", "sensor", "satellite", "latitude", "longitude"],
            kind="mergesort",
        ).reset_index(drop=True)
    else:
        combined_valid_df = _empty_canonical_dataframe()

    if rejected_frames:
        combined_rejected_df = pd.concat(rejected_frames, ignore_index=True)
    else:
        combined_rejected_df = _empty_canonical_dataframe()
        combined_rejected_df["rejection_reason"] = pd.Series(dtype="object")

    # 6. Assign 0.01-degree equal-angle spatial grid
    gridded_df = grid_observations(combined_valid_df, grid_size=resolved_grid_size)

    # 7. Apply 20-minute temporal deduplication policy
    deduped_df = deduplicate_observations(
        gridded_df,
        window_minutes=resolved_window_minutes,
        group_by_sensor=group_by_sensor,
        grid_size=resolved_grid_size,
    )

    # 8. Aggregate into FireCellDay
    fire_cell_day_df = aggregate_daily(deduped_df, grid_size=resolved_grid_size)

    # 9, 10 & 11. Write interim, processed, and metadata files
    mode_slug = mode.strip().lower()
    interim_region_dir = base_interim_dir / region_slug
    processed_region_dir = base_processed_dir / region_slug
    interim_region_dir.mkdir(parents=True, exist_ok=True)
    processed_region_dir.mkdir(parents=True, exist_ok=True)

    normalized_path = (
        interim_region_dir
        / f"{region_slug}_observations_normalized_{mode_slug}_{start_str}_{end_str}.csv"
    )
    deduplicated_path = (
        interim_region_dir
        / f"{region_slug}_observations_deduplicated_{mode_slug}_{start_str}_{end_str}.csv"
    )
    rejected_path = (
        interim_region_dir
        / f"{region_slug}_observations_rejected_{mode_slug}_{start_str}_{end_str}.csv"
    )
    fire_cell_day_path = (
        processed_region_dir
        / f"{region_slug}_fire_cell_day_{mode_slug}_{start_str}_{end_str}.csv"
    )
    metadata_path = (
        processed_region_dir
        / f"{region_slug}_run_metadata_{mode_slug}_{start_str}_{end_str}.json"
    )

    gridded_df.to_csv(normalized_path, index=False)
    deduped_df.to_csv(deduplicated_path, index=False)
    combined_rejected_df.to_csv(rejected_path, index=False)
    fire_cell_day_df.to_csv(fire_cell_day_path, index=False)

    valid_total = len(gridded_df)
    rejected_total = len(combined_rejected_df)
    deduped_total = len(deduped_df)
    modis_valid = int((gridded_df["sensor"] == "MODIS").sum()) if not gridded_df.empty else 0
    viirs_valid = int((gridded_df["sensor"] == "VIIRS").sum()) if not gridded_df.empty else 0
    modis_deduped = int((deduped_df["sensor"] == "MODIS").sum()) if not deduped_df.empty else 0
    viirs_deduped = int((deduped_df["sensor"] == "VIIRS").sum()) if not deduped_df.empty else 0

    metadata: dict[str, Any] = {
        "status": "completed",
        "region": region_slug,
        "bbox": validated_bbox,
        "start_date": start_str,
        "end_date": end_str,
        "mode": mode_slug,
        "sensor": sensor.strip().lower(),
        "grid_resolution_deg": resolved_grid_size,
        "temporal_dedup_window_minutes": resolved_window_minutes,
        "group_by_sensor": group_by_sensor,
        "products": products_processed,
        "product_summaries": product_summaries,
        "counts": {
            "raw_total": raw_total,
            "valid_total": valid_total,
            "rejected_total": rejected_total,
            "rejection_counts": aggregated_rejection_counts,
            "deduplicated_total": deduped_total,
            "duplicates_removed": valid_total - deduped_total,
            "fire_cell_day_total": len(fire_cell_day_df),
            "modis_valid_rows": modis_valid,
            "viirs_valid_rows": viirs_valid,
            "modis_deduplicated_rows": modis_deduped,
            "viirs_deduplicated_rows": viirs_deduped,
        },
        "output_paths": {
            "raw_csv_paths": raw_csv_paths,
            "normalized_observations_path": str(normalized_path),
            "deduplicated_observations_path": str(deduplicated_path),
            "rejected_observations_path": str(rejected_path),
            "fire_cell_day_path": str(fire_cell_day_path),
            "metadata_path": str(metadata_path),
        },
    }

    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "metadata": metadata,
        "normalized_df": gridded_df,
        "deduplicated_df": deduped_df,
        "rejected_df": combined_rejected_df,
        "fire_cell_day_df": fire_cell_day_df,
    }


def run_daily_update(
    *,
    region: str | None = None,
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
    """Run the end-to-end FIRMS pipeline update for an explicitly specified region and date interval."""
    return run_firms_pipeline(
        region=region,
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


def build_arg_parser(
    prog: str = "python -m pipeline.jobs.daily_update",
) -> argparse.ArgumentParser:
    """Create the CLI argument parser for the end-to-end FIRMS pipeline."""
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Run the end-to-end NASA FIRMS ingestion, normalization, quality control, "
            "0.01-deg spatial gridding, 20-min temporal deduplication, and FireCellDay pipeline."
        ),
    )
    parser.add_argument(
        "--region",
        type=str,
        default=None,
        help="Configured region name from config/regions.yaml (e.g. malaysia, indonesia, india, north_america, global, world).",
    )
    parser.add_argument(
        "--bbox",
        type=str,
        default=None,
        help="Explicit bounding box 'west,south,east,north' (overrides --region bbox).",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["sp", "nrt"],
        default="sp",
        help="FIRMS processing mode: 'sp' (Standard Processing archive) or 'nrt' (Near Real-Time).",
    )
    parser.add_argument(
        "--sensor",
        type=str,
        choices=["all", "modis", "viirs", "snpp", "noaa20", "noaa21"],
        default="all",
        help="Sensor filter: 'all', 'modis', 'viirs', or a specific VIIRS platform.",
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=None,
        help="Base directory for raw downloaded CSVs (defaults to DATA_RAW_DIR or ./data/raw).",
    )
    parser.add_argument(
        "--interim-dir",
        type=str,
        default=None,
        help="Base directory for normalized/QC interim CSVs (defaults to DATA_INTERIM_DIR or ./data/interim).",
    )
    parser.add_argument(
        "--processed-dir",
        type=str,
        default=None,
        help="Base directory for processed FireCellDay CSV and run metadata JSON (defaults to DATA_PROCESSED_DIR or ./data/processed).",
    )
    parser.add_argument(
        "--save-raw-chunks",
        action="store_true",
        help="Save individual <=5-day chunk CSV files alongside combined raw product CSVs.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    prog: str = "python -m pipeline.jobs.daily_update",
) -> int:
    """CLI entry point for the end-to-end NASA FIRMS pipeline."""
    parser = build_arg_parser(prog=prog)
    args = parser.parse_args(argv)
    load_dotenv_if_present()
    result = run_firms_pipeline(
        region=args.region,
        bbox=args.bbox,
        start_date=args.start_date,
        end_date=args.end_date,
        mode=args.mode,
        sensor=args.sensor,
        raw_dir=args.raw_dir,
        interim_dir=args.interim_dir,
        processed_dir=args.processed_dir,
        save_raw_chunks=args.save_raw_chunks,
    )
    meta = result["metadata"]
    counts = meta["counts"]
    paths = meta["output_paths"]
    print(
        f"[FIRMS Pipeline] region={meta['region']} range={meta['start_date']}..{meta['end_date']} "
        f"mode={meta['mode']} raw={counts['raw_total']} valid={counts['valid_total']} "
        f"rejected={counts['rejected_total']} deduped={counts['deduplicated_total']} "
        f"cells={counts['fire_cell_day_total']} -> {paths['fire_cell_day_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
