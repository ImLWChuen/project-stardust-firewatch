"""Data canonicalization, schema standardization, and confidence filtering."""
from __future__ import annotations

from typing import Any

import pandas as pd

from pipeline.preprocessing.normalize_fields import (
    DAYNIGHT_MAPPING,
    _is_missing,
    normalize_acq_date,
    normalize_acq_time,
    normalize_confidence,
    normalize_fields,
    normalize_satellite_name,
    normalize_sensor_name,
)
from pipeline.preprocessing.quality_control import filter_invalid_rows

REQUIRED_CANONICAL_COLUMNS = [
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "frp",
    "daynight",
]


def canonicalize_observation(record: dict[str, Any]) -> dict[str, Any]:
    """Standardize an individual raw fire record into the canonical observation schema.

    Uses the explicit satellite and sensor lookup tables from
    `pipeline.preprocessing.normalize_fields` so VIIRS platforms (such as
    NOAA-20 and NOAA-21) are never misclassified as MODIS.
    """
    if not isinstance(record, dict):
        raise TypeError("record must be a dict.")

    lat = float(record.get("latitude", 0.0))
    lon = float(record.get("longitude", 0.0))
    frp = float(record.get("frp", 0.0))
    acq_date = normalize_acq_date(record.get("acq_date")) or str(
        record.get("acq_date", "")
    ).strip()
    acq_time = normalize_acq_time(record.get("acq_time")) or str(
        record.get("acq_time", "0000")
    ).strip().zfill(4)

    raw_sat = record.get("satellite")
    mapped_sat, sat_sensor = normalize_satellite_name(raw_sat)

    raw_inst = record.get("instrument") if not _is_missing(record.get("instrument")) else record.get("sensor")
    mapped_inst = normalize_sensor_name(raw_inst)
    instrument = mapped_inst if mapped_inst is not None else sat_sensor

    satellite = mapped_sat
    if satellite is None and not _is_missing(raw_sat):
        satellite = str(raw_sat).strip()

    raw_conf, norm_conf = normalize_confidence(record.get("confidence"), instrument)
    confidence = raw_conf if raw_conf is not None else record.get("confidence")

    raw_dn = record.get("daynight") if not _is_missing(record.get("daynight")) else record.get("day_night")
    if _is_missing(raw_dn):
        daynight = None
    else:
        dn_str = str(raw_dn).strip()
        daynight = DAYNIGHT_MAPPING.get(dn_str.lower(), dn_str)

    return {
        "latitude": lat,
        "longitude": lon,
        "acq_date": acq_date,
        "acq_time": acq_time,
        "satellite": satellite,
        "instrument": instrument,
        "sensor": instrument,
        "confidence": confidence,
        "confidence_norm": norm_conf,
        "frp": frp,
        "daynight": daynight,
    }


def canonicalize_fire_dataframe(
    df: pd.DataFrame,
    min_confidence: float | None = None,
) -> pd.DataFrame:
    """Clean, normalize, and optionally filter a fire detection DataFrame."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")
    norm_df = normalize_fields(df)
    if min_confidence is not None:
        return filter_invalid_rows(norm_df, min_modis_confidence=float(min_confidence))
    return norm_df
