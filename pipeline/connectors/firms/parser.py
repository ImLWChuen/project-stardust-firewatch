"""Parser and response validator for NASA FIRMS CSV payloads."""
from __future__ import annotations

import io

import pandas as pd

DEFAULT_FIRMS_COLUMNS: tuple[str, ...] = (
    "latitude",
    "longitude",
    "brightness",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "confidence",
    "version",
    "bright_t31",
    "frp",
    "daynight",
)

_ERROR_PREFIXES: tuple[str, ...] = (
    "invalid",
    "error",
    "exceed",
    "map_key",
    "missing",
    "unauthorized",
    "forbidden",
    "not found",
    "service unavailable",
    "<!doctype",
    "<html",
)


class FIRMSAPIError(ValueError, RuntimeError):
    """Raised when NASA FIRMS returns a plain-text error or malformed payload."""


def validate_firms_response_body(csv_text: str) -> None:
    """Validate that a FIRMS response body is either empty or has a valid CSV header.

    NASA FIRMS frequently returns HTTP 200 OK with a plain-text error string
    (e.g. 'Invalid MAP_KEY.', 'Invalid coordinates', 'Exceeding allowed transaction limit').
    """
    if not isinstance(csv_text, str):
        raise TypeError("FIRMS response body must be a string.")

    stripped = csv_text.strip()
    if not stripped:
        return

    first_line = stripped.splitlines()[0].strip()
    lower_first = first_line.lower()

    if any(lower_first.startswith(prefix) for prefix in _ERROR_PREFIXES):
        raise FIRMSAPIError(f"FIRMS API returned an error response: {first_line}")

    if "," not in first_line:
        raise FIRMSAPIError(f"FIRMS API returned non-CSV response: {first_line}")

    header_cols = {col.strip().strip('"').lower() for col in first_line.split(",")}
    if "latitude" not in header_cols or "longitude" not in header_cols:
        raise FIRMSAPIError(
            f"FIRMS response is missing required 'latitude'/'longitude' columns: {first_line}"
        )


def parse_firms_csv(csv_text: str) -> pd.DataFrame:
    """Parse FIRMS CSV response text into a standard DataFrame.

    Handles empty or header-only responses safely and raises FIRMSAPIError
    when plain-text error messages are encountered.
    """
    if not isinstance(csv_text, str):
        raise TypeError("Cannot parse non-string as FIRMS CSV.")

    validate_firms_response_body(csv_text)

    stripped = csv_text.strip()
    if not stripped:
        return pd.DataFrame(columns=list(DEFAULT_FIRMS_COLUMNS))

    df = pd.read_csv(io.StringIO(stripped))
    return df
