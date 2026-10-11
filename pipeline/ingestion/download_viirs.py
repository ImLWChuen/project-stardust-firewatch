"""Download VIIRS (SNPP, NOAA-20, NOAA-21) raw fire detections from NASA FIRMS."""
from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date as date_type
from datetime import datetime
from pathlib import Path
from typing import Any

from pipeline.connectors.firms.client import FIRMSClient
from pipeline.connectors.firms.downloader import FIRMSDownloader
from pipeline.ingestion.download_modis import (
    GLOBAL_BBOX,
    GLOBAL_BBOX_STR,
    download_sensor_products,
    get_pipeline_data_dirs,
    get_raw_data_dir,
    load_dotenv_if_present,
    load_regions_config,
    resolve_region_bbox,
)

__all__ = [
    "GLOBAL_BBOX",
    "GLOBAL_BBOX_STR",
    "build_arg_parser",
    "download_viirs_data",
    "get_pipeline_data_dirs",
    "get_raw_data_dir",
    "load_regions_config",
    "main",
    "resolve_region_bbox",
]

_VALID_VIIRS_SENSORS = {
    "viirs",
    "snpp",
    "suomi-npp",
    "suomi_npp",
    "viirs_snpp",
    "noaa20",
    "noaa-20",
    "noaa_20",
    "viirs_noaa20",
    "noaa21",
    "noaa-21",
    "noaa_21",
    "viirs_noaa21",
}


def download_viirs_data(
    region: str | None = None,
    start_date: str | date_type | datetime | None = None,
    end_date: str | date_type | datetime | None = None,
    mode: str = "sp",
    *,
    sensor: str = "viirs",
    bbox: str | Sequence[int | float] | None = None,
    output_dir: str | Path | None = None,
    config_path: str | Path | None = None,
    client: FIRMSClient | None = None,
    downloader: FIRMSDownloader | None = None,
    save_raw_chunks: bool = False,
) -> list[dict[str, Any]]:
    """Download VIIRS (SNPP, NOAA-20, NOAA-21) fire detections for a region or bbox."""
    if not isinstance(sensor, str):
        raise TypeError("sensor must be a string.")
    sensor_norm = sensor.strip().lower()
    if sensor_norm not in _VALID_VIIRS_SENSORS:
        raise ValueError(
            f"Unsupported VIIRS sensor {sensor!r}. Expected one of: viirs, snpp, noaa20, noaa21."
        )

    return download_sensor_products(
        sensor=sensor_norm,
        region=region,
        bbox=bbox,
        start_date=start_date,
        end_date=end_date,
        mode=mode,
        output_dir=output_dir,
        config_path=config_path,
        client=client,
        downloader=downloader,
        save_raw_chunks=save_raw_chunks,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser for VIIRS ingestion."""
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.ingestion.download_viirs",
        description="Download NASA FIRMS VIIRS active fire detections for a region or bounding box.",
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
        choices=["viirs", "snpp", "noaa20", "noaa21"],
        default="viirs",
        help="VIIRS platform filter ('viirs' for all available VIIRS platforms, or a single platform).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Base output directory for raw CSV files (defaults to DATA_RAW_DIR or ./data/raw).",
    )
    parser.add_argument(
        "--save-raw-chunks",
        action="store_true",
        help="Save individual <=5-day chunk CSV files alongside the combined CSV.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for VIIRS data ingestion."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    load_dotenv_if_present()
    results = download_viirs_data(
        region=args.region,
        bbox=args.bbox,
        start_date=args.start_date,
        end_date=args.end_date,
        mode=args.mode,
        sensor=args.sensor,
        output_dir=args.output_dir,
        save_raw_chunks=args.save_raw_chunks,
    )
    for item in results:
        print(
            f"[{item['source']}] region={item['region']} "
            f"range={item['start_date']}..{item['end_date']} "
            f"rows={item['row_count']} -> {item['output_path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
