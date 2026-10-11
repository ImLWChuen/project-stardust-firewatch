"""Download MODIS raw fire detections from NASA FIRMS Area API."""
from __future__ import annotations

import argparse
import asyncio
import os
from collections.abc import Sequence
from datetime import date as date_type
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from pipeline.connectors.firms.client import (
    FIRMSClient,
    parse_bbox,
    validate_bbox,
    validate_query_date,
)
from pipeline.connectors.firms.downloader import FIRMSDownloader
from pipeline.connectors.firms.parser import parse_firms_csv
from pipeline.connectors.firms.products import get_products_for_sensor

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGIONS_CONFIG_PATH = REPO_ROOT / "config" / "regions.yaml"
DEFAULT_RAW_DIR = "./data/raw"
DEFAULT_INTERIM_DIR = "./data/interim"
DEFAULT_PROCESSED_DIR = "./data/processed"
GLOBAL_BBOX: tuple[float, float, float, float] = (-180.0, -90.0, 180.0, 90.0)
GLOBAL_BBOX_STR = "-180.0,-90.0,180.0,90.0"


def load_dotenv_if_present(dotenv_path: str | Path | None = None) -> None:
    """Populate os.environ from a .env file if present without logging secrets."""
    path = Path(dotenv_path) if dotenv_path is not None else REPO_ROOT / ".env"
    if not path.is_file():
        return
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def get_pipeline_data_dirs() -> dict[str, Path]:
    """Return resolved raw, interim, and processed data directories from environment."""
    return {
        "raw": Path(os.environ.get("DATA_RAW_DIR", DEFAULT_RAW_DIR)),
        "interim": Path(os.environ.get("DATA_INTERIM_DIR", DEFAULT_INTERIM_DIR)),
        "processed": Path(os.environ.get("DATA_PROCESSED_DIR", DEFAULT_PROCESSED_DIR)),
    }


def get_raw_data_dir(output_dir: str | Path | None = None) -> Path:
    """Resolve the base directory for storing raw downloaded FIRMS CSVs."""
    if output_dir is not None:
        if not isinstance(output_dir, (str, Path)):
            raise TypeError("output_dir must be a string or Path.")
        cleaned = str(output_dir).strip()
        if not cleaned:
            raise ValueError("output_dir cannot be an empty string.")
        return Path(cleaned)
    return get_pipeline_data_dirs()["raw"]


def load_regions_config(
    config_path: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Load and validate configured regions from config/regions.yaml."""
    path = (
        Path(config_path)
        if config_path is not None
        else DEFAULT_REGIONS_CONFIG_PATH
    )
    if not path.is_file():
        raise FileNotFoundError(f"Regions configuration file not found: {path}")

    with open(path, encoding="utf-8") as f:
        payload = yaml.safe_load(f)

    if not isinstance(payload, dict) or not isinstance(payload.get("regions"), dict):
        raise TypeError(
            f"Malformed regions configuration in {path}: expected top-level 'regions' mapping."
        )

    validated_regions: dict[str, dict[str, Any]] = {
        "global": {
            "name": "Global (World)",
            "bbox": list(GLOBAL_BBOX),
            "bbox_str": GLOBAL_BBOX_STR,
        },
        "world": {
            "name": "Global (World)",
            "bbox": list(GLOBAL_BBOX),
            "bbox_str": GLOBAL_BBOX_STR,
        },
    }

    for raw_key, raw_entry in payload["regions"].items():
        if not isinstance(raw_key, str):
            raise TypeError("Region keys in regions.yaml must be strings.")
        if not raw_key.strip():
            raise ValueError("Region keys in regions.yaml must be non-empty strings.")
        if not isinstance(raw_entry, dict):
            raise TypeError(f"Region {raw_key!r} in {path} must be a mapping.")
        if "bbox" not in raw_entry:
            raise ValueError(
                f"Region {raw_key!r} in {path} is missing a 'bbox' definition."
            )
        try:
            coords = parse_bbox(raw_entry["bbox"])
            bbox_str = validate_bbox(list(coords))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid bbox for region {raw_key!r} in {path}: {exc}"
            ) from exc

        key = raw_key.strip().lower()
        validated_regions[key] = {
            "name": str(raw_entry.get("name", raw_key)),
            "bbox": list(coords),
            "bbox_str": bbox_str,
        }

    if "global" in validated_regions:
        validated_regions["world"] = dict(validated_regions["global"])

    return validated_regions


def resolve_region_bbox(
    region: str | None = None,
    bbox: str | Sequence[int | float] | None = None,
    config_path: str | Path | None = None,
) -> tuple[str, str]:
    """Resolve a (region_slug, validated_bbox_str) pair from region name or explicit bbox."""
    if bbox is not None:
        bbox_str = validate_bbox(bbox)
        if region is not None:
            if not isinstance(region, str):
                raise TypeError("region must be a string when provided.")
            slug = region.strip().lower() or "custom"
        else:
            slug = "custom"
        return slug, bbox_str

    if region is None:
        raise ValueError(
            "Explicit 'region' or 'bbox' must be provided for FIRMS data ingestion."
        )
    if not isinstance(region, str):
        raise TypeError("region must be a string.")

    region_key = region.strip().lower()
    if not region_key:
        raise ValueError("region must be a non-empty string.")

    regions = load_regions_config(config_path=config_path)
    if region_key not in regions:
        available = ", ".join(sorted(regions.keys()))
        raise ValueError(
            f"Unknown region {region!r}. Available regions: {available}"
        )

    return region_key, regions[region_key]["bbox_str"]


def download_sensor_products(
    *,
    sensor: str,
    region: str | None = None,
    bbox: str | Sequence[int | float] | None = None,
    start_date: str | date_type | datetime | None = None,
    end_date: str | date_type | datetime | None = None,
    mode: str = "sp",
    output_dir: str | Path | None = None,
    config_path: str | Path | None = None,
    client: FIRMSClient | None = None,
    downloader: FIRMSDownloader | None = None,
    save_raw_chunks: bool = False,
) -> list[dict[str, Any]]:
    """Download FIRMS CSV data for all products matching sensor and mode over a date range."""
    region_slug, validated_bbox = resolve_region_bbox(
        region=region,
        bbox=bbox,
        config_path=config_path,
    )
    if start_date is None or end_date is None:
        raise ValueError(
            "Explicit 'start_date' and 'end_date' (YYYY-MM-DD) are required for FIRMS ingestion."
        )

    start_str = validate_query_date(start_date)
    end_str = validate_query_date(end_date)
    if start_str is None or end_str is None:
        raise ValueError("start_date and end_date are required.")
    if end_str < start_str:
        raise ValueError(
            f"end_date ({end_str}) must be on or after start_date ({start_str})."
        )

    products = get_products_for_sensor(sensor=sensor, mode=mode)
    base_raw_dir = get_raw_data_dir(output_dir)
    region_raw_dir = base_raw_dir / region_slug

    active_downloader = downloader
    if active_downloader is None:
        active_client = client if client is not None else FIRMSClient()
        active_downloader = FIRMSDownloader(
            client=active_client,
            dest_dir=str(region_raw_dir),
        )

    results: list[dict[str, Any]] = []
    for product in products:
        output_filename = f"{region_slug}_{product}_{start_str}_{end_str}.csv"
        out_path = asyncio.run(
            active_downloader.download_date_range(
                source=product,
                bbox=validated_bbox,
                start_date=start_str,
                end_date=end_str,
                output_filename=output_filename,
                save_raw_chunks=save_raw_chunks,
            )
        )
        with open(out_path, encoding="utf-8") as f:
            csv_content = f.read()
        df = parse_firms_csv(csv_content)
        dl_meta = active_downloader.last_download_metadata or {}
        results.append(
            {
                "region": region_slug,
                "bbox": validated_bbox,
                "sensor": sensor.lower(),
                "source": product,
                "mode": mode.strip().lower(),
                "start_date": start_str,
                "end_date": end_str,
                "output_path": out_path,
                "row_count": len(df),
                "is_empty": bool(df.empty),
                "chunks": dl_meta.get("chunks", []),
                "chunk_lengths": dl_meta.get("chunk_lengths", []),
                "raw_chunk_paths": dl_meta.get("raw_chunk_paths", []),
            }
        )

    return results


def download_modis_data(
    region: str | None = None,
    start_date: str | date_type | datetime | None = None,
    end_date: str | date_type | datetime | None = None,
    mode: str = "sp",
    *,
    bbox: str | Sequence[int | float] | None = None,
    output_dir: str | Path | None = None,
    config_path: str | Path | None = None,
    client: FIRMSClient | None = None,
    downloader: FIRMSDownloader | None = None,
    save_raw_chunks: bool = False,
) -> list[dict[str, Any]]:
    """Download MODIS (SP or NRT) fire detections for a configured region or bbox."""
    return download_sensor_products(
        sensor="modis",
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
    """Create the CLI argument parser for MODIS ingestion."""
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.ingestion.download_modis",
        description="Download NASA FIRMS MODIS active fire detections for a region or bounding box.",
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
    """CLI entry point for MODIS data ingestion."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    load_dotenv_if_present()
    results = download_modis_data(
        region=args.region,
        bbox=args.bbox,
        start_date=args.start_date,
        end_date=args.end_date,
        mode=args.mode,
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
