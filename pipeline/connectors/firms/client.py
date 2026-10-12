"""Client for interacting with the NASA FIRMS Area API."""
from __future__ import annotations

import math
import os
from collections.abc import Sequence
from datetime import date as date_type
from datetime import datetime

import httpx

from pipeline.connectors.firms.parser import (
    FIRMSAPIError,
    validate_firms_response_body,
)
from pipeline.connectors.firms.products import validate_product

DEFAULT_FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api"
MIN_DAY_RANGE = 1
MAX_DAY_RANGE = 5

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


def validate_day_range(day_range: int) -> int:
    """Validate that day_range is an integer in [1, 5] per NASA FIRMS Area API limits."""
    if isinstance(day_range, bool) or not isinstance(day_range, int):
        raise TypeError(
            f"day_range must be an integer between {MIN_DAY_RANGE} and {MAX_DAY_RANGE}, got {day_range!r}."
        )
    if day_range < MIN_DAY_RANGE or day_range > MAX_DAY_RANGE:
        raise ValueError(
            f"day_range must be between {MIN_DAY_RANGE} and {MAX_DAY_RANGE} inclusive, got {day_range}."
        )
    return day_range


def parse_bbox(bbox: str | Sequence[int | float]) -> tuple[float, float, float, float]:
    """Parse and validate a bounding box in (west, south, east, north) order."""
    if isinstance(bbox, str):
        parts = [p.strip() for p in bbox.split(",") if p.strip() != ""]
        if len(parts) != 4:
            raise ValueError(
                f"bbox must have 4 comma-separated coordinates 'west,south,east,north', got {bbox!r}."
            )
        try:
            coords = tuple(float(p) for p in parts)
        except ValueError as exc:
            raise ValueError(
                f"bbox coordinates must be numeric 'west,south,east,north', got {bbox!r}."
            ) from exc
    elif isinstance(bbox, (list, tuple)):
        if len(bbox) != 4:
            raise ValueError(
                f"bbox sequence must contain 4 elements (west, south, east, north), got {len(bbox)}."
            )
        try:
            coords = tuple(float(c) for c in bbox)
        except (TypeError, ValueError) as exc:
            raise ValueError("bbox coordinates must be numeric.") from exc
    else:
        raise TypeError(
            "bbox must be a comma-separated string 'west,south,east,north' or 4-element sequence."
        )

    west, south, east, north = coords
    if not all(math.isfinite(val) for val in coords):
        raise ValueError("bbox coordinates must be finite numbers.")
    if west < -180.0 or west > 180.0 or east < -180.0 or east > 180.0:
        raise ValueError(
            f"Longitude bounds (west={west}, east={east}) must be within [-180, 180]."
        )
    if south < -90.0 or south > 90.0 or north < -90.0 or north > 90.0:
        raise ValueError(
            f"Latitude bounds (south={south}, north={north}) must be within [-90, 90]."
        )
    if west >= east:
        raise ValueError(
            f"Invalid bbox order: west ({west}) must be strictly less than east ({east})."
        )
    if south >= north:
        raise ValueError(
            f"Invalid bbox order: south ({south}) must be strictly less than north ({north})."
        )
    return west, south, east, north


def validate_bbox(bbox: str | Sequence[int | float]) -> str:
    """Validate bbox and return a normalized 'west,south,east,north' string."""
    west, south, east, north = parse_bbox(bbox)
    if isinstance(bbox, str):
        return ",".join(p.strip() for p in bbox.split(","))
    return f"{west},{south},{east},{north}"


def validate_query_date(
    query_date: str | date_type | datetime | None
) -> str | None:
    """Validate optional historical query date and format as YYYY-MM-DD."""
    if query_date is None:
        return None
    if isinstance(query_date, datetime):
        return query_date.strftime("%Y-%m-%d")
    if isinstance(query_date, date_type):
        return query_date.strftime("%Y-%m-%d")
    if isinstance(query_date, str):
        cleaned = query_date.strip()
        if not cleaned:
            raise ValueError("date cannot be an empty string when provided.")
        if len(cleaned) != 10:
            raise ValueError(f"date must be in YYYY-MM-DD format, got {query_date!r}.")
        try:
            datetime.strptime(cleaned, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(
                f"date must be a valid calendar date in YYYY-MM-DD format, got {query_date!r}."
            ) from exc
        return cleaned
    raise TypeError(
        f"date must be a YYYY-MM-DD string, datetime.date, or None, got {type(query_date).__name__}."
    )


class FIRMSClient:
    """Client for interacting with the NASA FIRMS Area API."""

    def __init__(
        self,
        map_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ):
        resolved_key = map_key if map_key is not None else os.environ.get("FIRMS_MAP_KEY", "")
        self.map_key = resolved_key.strip() if isinstance(resolved_key, str) else ""
        if not self.map_key or self.map_key == "your_firms_map_key_here":
            raise ValueError(
                "NASA FIRMS API key is required. Pass map_key or set a valid FIRMS_MAP_KEY environment variable."
            )

        resolved_url = (
            base_url
            if base_url is not None
            else os.environ.get("FIRMS_BASE_URL", DEFAULT_FIRMS_BASE_URL)
        )
        self.base_url = (resolved_url or DEFAULT_FIRMS_BASE_URL).strip().rstrip("/")
        self.timeout = float(timeout)

    def __repr__(self) -> str:
        return f"FIRMSClient(base_url={self.base_url!r}, map_key='***', timeout={self.timeout})"

    def build_area_url(
        self,
        source: str,
        bbox: str | Sequence[int | float],
        day_range: int = 1,
        date: str | date_type | datetime | None = None,
    ) -> str:
        """Construct and validate a FIRMS Area CSV endpoint URL."""
        validated_source = validate_product(source)
        validated_bbox = validate_bbox(bbox)
        validated_days = validate_day_range(day_range)
        validated_date = validate_query_date(date)

        url = f"{self.base_url}/area/csv/{self.map_key}/{validated_source}/{validated_bbox}/{validated_days}"
        if validated_date is not None:
            url = f"{url}/{validated_date}"
        return url

    async def fetch_area_response(
        self,
        source: str,
        bbox: str | Sequence[int | float],
        day_range: int = 1,
        date: str | date_type | datetime | None = None,
    ) -> httpx.Response:
        """Execute validated GET request against FIRMS Area API and return httpx.Response."""
        url = self.build_area_url(source=source, bbox=bbox, day_range=day_range, date=date)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url)
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                # Hide API key in error message for security
                safe_url = url.replace(self.map_key, "***") if self.map_key else url
                raise FIRMSAPIError(
                    f"FIRMS API HTTP {resp.status_code} for {safe_url}"
                ) from None
            validate_firms_response_body(resp.text)
            return resp

    async def fetch_area_csv(
        self,
        source: str,
        bbox: str | Sequence[int | float],
        day_range: int = 1,
        date: str | date_type | datetime | None = None,
    ) -> str:
        """Fetch raw CSV text for a bounding box and 1-5 day window from NASA FIRMS."""
        resp = await self.fetch_area_response(
            source=source,
            bbox=bbox,
            day_range=day_range,
            date=date,
        )
        return resp.text
