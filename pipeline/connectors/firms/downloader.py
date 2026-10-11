"""Download management with deterministic <=5-day chunking and CSV merging."""
from __future__ import annotations

import asyncio
import os
from collections.abc import Sequence
from datetime import date as date_type
from datetime import datetime, timedelta
from typing import Any

from pipeline.connectors.firms.client import (
    MAX_DAY_RANGE,
    FIRMSClient,
    validate_bbox,
    validate_day_range,
    validate_query_date,
)
from pipeline.connectors.firms.parser import validate_firms_response_body
from pipeline.connectors.firms.products import validate_product


def _write_text_file(path: str, content: str) -> None:
    """Write UTF-8 text content to disk synchronously."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def chunk_date_range(
    start_date: str | date_type | datetime,
    end_date: str | date_type | datetime,
    max_days: int = MAX_DAY_RANGE,
) -> list[tuple[str, int]]:
    """Split an inclusive [start_date, end_date] interval into chunks of at most max_days (1..5).

    Returns:
        List of (chunk_start_yyyy_mm_dd, chunk_day_range) tuples.
        For example, a 31-day month (2025-01-01..2025-01-31) with max_days=5 yields
        7 chunks with lengths [5, 5, 5, 5, 5, 5, 1].
    """
    validate_day_range(max_days)
    start_str = validate_query_date(start_date)
    end_str = validate_query_date(end_date)
    if start_str is None or end_str is None:
        raise ValueError("start_date and end_date are required.")

    start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_str, "%Y-%m-%d").date()
    if end_dt < start_dt:
        raise ValueError(
            f"end_date ({end_str}) must be on or after start_date ({start_str})."
        )

    chunks: list[tuple[str, int]] = []
    current_dt = start_dt
    while current_dt <= end_dt:
        remaining_days = (end_dt - current_dt).days + 1
        span = min(max_days, remaining_days)
        chunks.append((current_dt.strftime("%Y-%m-%d"), span))
        current_dt += timedelta(days=span)

    return chunks


def combine_csv_chunks(csv_chunks: Sequence[str]) -> str:
    """Combine multiple FIRMS CSV response strings into one CSV without duplicate headers."""
    header: str | None = None
    data_rows: list[str] = []

    for chunk in csv_chunks:
        if not chunk or not chunk.strip():
            continue
        validate_firms_response_body(chunk)
        lines = [line.strip() for line in chunk.strip().splitlines() if line.strip()]
        if not lines:
            continue

        chunk_header = lines[0]
        if header is None:
            header = chunk_header

        for row in lines[1:]:
            if row == header or row == chunk_header:
                continue
            data_rows.append(row)

    if header is None:
        return ""
    if not data_rows:
        return f"{header}\n"
    return "\n".join([header, *data_rows]) + "\n"


class FIRMSDownloader:
    """Manages downloading and persisting NASA FIRMS CSV datasets."""

    def __init__(self, client: FIRMSClient | None = None, dest_dir: str = "."):
        self.client = client
        self.dest_dir = dest_dir
        self.last_download_metadata: dict[str, Any] | None = None
        if self.dest_dir:
            os.makedirs(self.dest_dir, exist_ok=True)

    @staticmethod
    def chunk_date_range(
        start_date: str | date_type | datetime,
        end_date: str | date_type | datetime,
        max_days: int = MAX_DAY_RANGE,
    ) -> list[tuple[str, int]]:
        """Delegate to module-level deterministic chunk_date_range helper."""
        return chunk_date_range(start_date=start_date, end_date=end_date, max_days=max_days)

    def _require_client(self) -> FIRMSClient:
        if self.client is None:
            raise ValueError("FIRMSDownloader requires a configured FIRMSClient instance.")
        return self.client

    def _prepare_output_path(self, output_filename: str) -> str:
        os.makedirs(self.dest_dir, exist_ok=True)
        out_path = os.path.join(self.dest_dir, output_filename)
        parent_dir = os.path.dirname(out_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        return out_path

    async def download_bbox(
        self,
        source: str,
        bbox: str | Sequence[int | float],
        output_filename: str,
        day_range: int = 1,
        date: str | date_type | datetime | None = None,
    ) -> str:
        """Download a single 1..5 day FIRMS request for a bounding box and save to disk."""
        client = self._require_client()
        if day_range == 1 and date is None:
            content = await client.fetch_area_csv(source, bbox)
        else:
            content = await client.fetch_area_csv(
                source, bbox, day_range=day_range, date=date
            )

        out_path = self._prepare_output_path(output_filename)
        await asyncio.to_thread(_write_text_file, out_path, content)

        self.last_download_metadata = {
            "source": source,
            "bbox": bbox,
            "day_range": day_range,
            "date": validate_query_date(date),
            "output_path": out_path,
        }
        return out_path

    async def download_date_range(
        self,
        source: str,
        bbox: str | Sequence[int | float],
        start_date: str | date_type | datetime,
        end_date: str | date_type | datetime,
        output_filename: str | None = None,
        save_raw_chunks: bool = False,
    ) -> str:
        """Download an arbitrary date range by chunking into <=5-day requests and merging CSVs."""
        client = self._require_client()
        validated_source = validate_product(source)
        validated_bbox = validate_bbox(bbox)
        start_str = validate_query_date(start_date)
        end_str = validate_query_date(end_date)
        chunks = chunk_date_range(start_str, end_str, max_days=MAX_DAY_RANGE)

        raw_payloads: list[str] = []
        raw_chunk_paths: list[str] = []

        for chunk_start, chunk_days in chunks:
            csv_text = await client.fetch_area_csv(
                validated_source,
                validated_bbox,
                day_range=chunk_days,
                date=chunk_start,
            )
            raw_payloads.append(csv_text)

            if save_raw_chunks:
                chunk_fname = f"{validated_source}_{chunk_start}_{chunk_days}d.csv"
                chunk_path = self._prepare_output_path(os.path.join("chunks", chunk_fname))
                await asyncio.to_thread(_write_text_file, chunk_path, csv_text)
                raw_chunk_paths.append(chunk_path)

        combined_csv = combine_csv_chunks(raw_payloads)
        final_filename = (
            output_filename
            if output_filename
            else f"{validated_source}_{start_str}_{end_str}.csv"
        )
        out_path = self._prepare_output_path(final_filename)
        await asyncio.to_thread(_write_text_file, out_path, combined_csv)

        self.last_download_metadata = {
            "source": validated_source,
            "bbox": validated_bbox,
            "start_date": start_str,
            "end_date": end_str,
            "chunks": chunks,
            "chunk_lengths": [days for _, days in chunks],
            "raw_chunk_paths": raw_chunk_paths,
            "output_path": out_path,
        }
        return out_path
