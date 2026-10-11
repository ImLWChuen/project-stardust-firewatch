"""Backend FIRMS downloader delegating to canonical pipeline downloader."""
from __future__ import annotations

from pipeline.connectors.firms.downloader import (
    FIRMSDownloader as CanonicalFIRMSDownloader,
)
from pipeline.connectors.firms.downloader import (
    chunk_date_range,
    combine_csv_chunks,
)

__all__ = [
    "FIRMSDownloader",
    "chunk_date_range",
    "combine_csv_chunks",
]


class FIRMSDownloader(CanonicalFIRMSDownloader):
    """Backend FIRMS downloader preserving legacy `download_country` stub."""

    def download_country(self, country_code: str, date: str):
        pass
