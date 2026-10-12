"""Backend FIRMS client delegating to canonical pipeline connector."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_type
from datetime import datetime

import httpx

from pipeline.connectors.firms.client import (
    DEFAULT_FIRMS_BASE_URL,
    MAX_DAY_RANGE,
    MIN_DAY_RANGE,
    FIRMSAPIError,
    parse_bbox,
    validate_bbox,
    validate_day_range,
    validate_query_date,
)
from pipeline.connectors.firms.client import (
    FIRMSClient as CanonicalFIRMSClient,
)

__all__ = [
    "DEFAULT_FIRMS_BASE_URL",
    "MAX_DAY_RANGE",
    "MIN_DAY_RANGE",
    "FIRMSAPIError",
    "FIRMSClient",
    "parse_bbox",
    "validate_bbox",
    "validate_day_range",
    "validate_query_date",
]


class FIRMSClient(CanonicalFIRMSClient):
    """Backend FIRMS client preserving legacy `fetch_area` method."""

    def __init__(
        self,
        map_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the client with an optional map key, base URL, and request timeout."""
        super().__init__(map_key=map_key, base_url=base_url, timeout=timeout)

    async def fetch_area(
        self,
        source: str,
        bbox: str | Sequence[int | float],
        days: int = 1,
        date: str | date_type | datetime | None = None,
    ) -> httpx.Response:
        """Fetch FIRMS area data and return the validated httpx.Response."""
        return await self.fetch_area_response(
            source=source,
            bbox=bbox,
            day_range=days,
            date=date,
        )
