"""Standardize column names and values across NASA FIRMS MODIS and VIIRS schemas."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from pipeline.connectors.firms.products import PRODUCT_METADATA, PRODUCTS

CANONICAL_COLUMNS: tuple[str, ...] = (
    "latitude",
    "longitude",
    "acq_datetime",
    "acq_date",
    "acq_time",
    "sensor",
    "instrument",
    "satellite",
    "confidence",
    "confidence_norm",
    "brightness",
    "frp",
    "scan",
    "track",
    "daynight",
    "source_product",
)

# Explicit mapping from raw FIRMS satellite identifiers to (canonical_satellite, canonical_sensor)
SATELLITE_MAPPING: dict[str, tuple[str, str]] = {
    "terra": ("Terra", "MODIS"),
    "t": ("Terra", "MODIS"),
    "eos-terra": ("Terra", "MODIS"),
    "eos_terra": ("Terra", "MODIS"),
    "modis_terra": ("Terra", "MODIS"),
    "aqua": ("Aqua", "MODIS"),
    "a": ("Aqua", "MODIS"),
    "eos-aqua": ("Aqua", "MODIS"),
    "eos_aqua": ("Aqua", "MODIS"),
    "modis_aqua": ("Aqua", "MODIS"),
    "n": ("Suomi-NPP", "VIIRS"),
    "snpp": ("Suomi-NPP", "VIIRS"),
    "suomi-npp": ("Suomi-NPP", "VIIRS"),
    "suomi_npp": ("Suomi-NPP", "VIIRS"),
    "suomi npp": ("Suomi-NPP", "VIIRS"),
    "npp": ("Suomi-NPP", "VIIRS"),
    "viirs_snpp": ("Suomi-NPP", "VIIRS"),
    "1": ("NOAA-20", "VIIRS"),
    "n20": ("NOAA-20", "VIIRS"),
    "noaa-20": ("NOAA-20", "VIIRS"),
    "noaa_20": ("NOAA-20", "VIIRS"),
    "noaa20": ("NOAA-20", "VIIRS"),
    "j1": ("NOAA-20", "VIIRS"),
    "jpss-1": ("NOAA-20", "VIIRS"),
    "jpss1": ("NOAA-20", "VIIRS"),
    "viirs_noaa20": ("NOAA-20", "VIIRS"),
    "2": ("NOAA-21", "VIIRS"),
    "n21": ("NOAA-21", "VIIRS"),
    "noaa-21": ("NOAA-21", "VIIRS"),
    "noaa_21": ("NOAA-21", "VIIRS"),
    "noaa21": ("NOAA-21", "VIIRS"),
    "j2": ("NOAA-21", "VIIRS"),
    "jpss-2": ("NOAA-21", "VIIRS"),
    "jpss2": ("NOAA-21", "VIIRS"),
    "viirs_noaa21": ("NOAA-21", "VIIRS"),
}

SENSOR_MAPPING: dict[str, str] = {
    "modis": "MODIS",
    "modis_nrt": "MODIS",
    "modis_sp": "MODIS",
    "modis_terra": "MODIS",
    "modis_aqua": "MODIS",
    "viirs": "VIIRS",
    "viirs_snpp": "VIIRS",
    "viirs_noaa20": "VIIRS",
    "viirs_noaa21": "VIIRS",
    "viirs_snpp_nrt": "VIIRS",
    "viirs_snpp_sp": "VIIRS",
    "viirs_noaa20_nrt": "VIIRS",
    "viirs_noaa20_sp": "VIIRS",
    "viirs_noaa21_nrt": "VIIRS",
}

SENSOR_PLATFORMS: dict[str, frozenset[str]] = {
    "MODIS": frozenset({"Terra", "Aqua"}),
    "VIIRS": frozenset({"Suomi-NPP", "NOAA-20", "NOAA-21"}),
}

VIIRS_CONFIDENCE_MAPPING: dict[str, str] = {
    "l": "low",
    "low": "low",
    "n": "nominal",
    "nominal": "nominal",
    "h": "high",
    "high": "high",
}

DAYNIGHT_MAPPING: dict[str, str] = {
    "d": "D",
    "day": "D",
    "n": "N",
    "night": "N",
}

_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "latitude": ("latitude", "lat"),
    "longitude": ("longitude", "lon", "long"),
    "acq_date": ("acq_date", "date"),
    "acq_time": ("acq_time", "time"),
    "acq_datetime": ("acq_datetime", "timestamp", "datetime"),
    "sensor": ("sensor", "instrument"),
    "satellite": ("satellite", "sat"),
    "confidence": ("confidence", "conf"),
    "brightness": ("brightness",),
    "bright_ti4": ("bright_ti4",),
    "frp": ("frp",),
    "scan": ("scan",),
    "track": ("track",),
    "daynight": ("daynight", "day_night"),
    "source_product": ("source_product", "product", "source"),
}


def _is_missing(value: Any) -> bool:
    """Return True if value is None, NaN, or pd.NA."""
    if value is None or value is pd.NA:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return bool(pd.isna(value))


def normalize_source_product(value: Any) -> str | None:
    """Normalize a known FIRMS product identifier or return None if missing/unknown."""
    if _is_missing(value):
        return None
    text = str(value).strip().upper()
    return PRODUCTS.get(text)


def normalize_sensor_name(value: Any) -> str | None:
    """Normalize a sensor/instrument identifier to 'MODIS' or 'VIIRS'."""
    if _is_missing(value):
        return None
    text = str(value).strip().lower()
    return SENSOR_MAPPING.get(text)


def normalize_satellite_name(value: Any) -> tuple[str | None, str | None]:
    """Normalize a satellite identifier to (canonical_satellite, canonical_sensor)."""
    if _is_missing(value):
        return None, None
    if isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value).strip().lower()
    return SATELLITE_MAPPING.get(text, (None, None))


def normalize_confidence(value: Any, sensor: str | None) -> tuple[Any, str | None]:
    """Normalize raw confidence according to sensor scale.

    - MODIS uses a numeric 0-100 scale:
      [0, 30) -> 'low', [30, 80) -> 'nominal', [80, 100] -> 'high'.
    - VIIRS uses categorical codes ('l'/'low', 'n'/'nominal', 'h'/'high').
    - Preserves the original raw value in the first return element and returns
      canonical 'low'/'nominal'/'high' (or None if invalid) in the second.
    """
    if _is_missing(value) or isinstance(value, bool):
        return None, None

    if sensor == "MODIS":
        if isinstance(value, (int, float, np.number)):
            num_val = float(value)
        elif isinstance(value, str):
            stripped = value.strip()
            try:
                num_val = float(stripped)
            except ValueError:
                return stripped, None
        else:
            return value, None

        if not math.isfinite(num_val) or num_val < 0.0 or num_val > 100.0:
            raw_out: Any = int(num_val) if math.isfinite(num_val) and num_val.is_integer() else num_val
            return raw_out, None

        raw_clean: Any = int(num_val) if num_val.is_integer() else num_val
        if num_val < 30.0:
            return raw_clean, "low"
        if num_val < 80.0:
            return raw_clean, "nominal"
        return raw_clean, "high"

    if sensor == "VIIRS":
        if not isinstance(value, str):
            return value, None
        stripped = value.strip()
        norm = VIIRS_CONFIDENCE_MAPPING.get(stripped.lower())
        return stripped, norm

    # Unknown sensor: preserve raw confidence but do not guess scale
    return value, None


def normalize_acq_time(value: Any) -> str | None:
    """Normalize acquisition time into a 4-digit UTC HHMM string ('0000'-'2359').

    Returns None if the time cannot be parsed as a valid 24-hour HHMM value.
    """
    if _is_missing(value) or isinstance(value, bool):
        return None

    if isinstance(value, (int, np.integer)):
        if value < 0 or value > 2359:
            return None
        candidate = f"{int(value):04d}"
    elif isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)) or not float(value).is_integer():
            return None
        int_val = int(value)
        if int_val < 0 or int_val > 2359:
            return None
        candidate = f"{int_val:04d}"
    elif isinstance(value, str):
        stripped = value.strip()
        # Support HH:MM or HH:MM:00 format as well as HHMM / HMM / MM / M
        if ":" in stripped:
            parts = stripped.split(":")
            if (len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()) or (
                len(parts) == 3
                and parts[0].isdigit()
                and parts[1].isdigit()
                and parts[2] in ("0", "00")
            ):
                candidate = f"{int(parts[0]):02d}{int(parts[1]):02d}"
            else:
                return None
        elif stripped.isdigit():
            if len(stripped) > 4:
                return None
            candidate = stripped.zfill(4)
        else:
            try:
                float_val = float(stripped)
            except ValueError:
                return None
            if not math.isfinite(float_val) or not float_val.is_integer():
                return None
            int_val = int(float_val)
            if int_val < 0 or int_val > 2359:
                return None
            candidate = f"{int_val:04d}"
    else:
        return None

    if len(candidate) != 4 or not candidate.isdigit():
        return None

    hour = int(candidate[:2])
    minute = int(candidate[2:])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None

    return candidate


def normalize_acq_date(value: Any) -> str | None:
    """Normalize acquisition date into a 'YYYY-MM-DD' string, or None if invalid."""
    if _is_missing(value) or isinstance(value, bool):
        return None

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")

    text = str(value).strip()
    if len(text) != 10:
        return None
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None
    return parsed.strftime("%Y-%m-%d")


def _parse_row_timestamp(
    raw_date: Any,
    raw_time: Any,
    raw_datetime: Any = None,
) -> tuple[pd.Timestamp | pd.NaT, str | None, str | None]:
    """Parse date, time, or full datetime into (utc_timestamp, acq_date, acq_time)."""
    norm_date = normalize_acq_date(raw_date)
    norm_time = normalize_acq_time(raw_time)

    if norm_date is not None and norm_time is not None:
        ts = pd.Timestamp(
            year=int(norm_date[0:4]),
            month=int(norm_date[5:7]),
            day=int(norm_date[8:10]),
            hour=int(norm_time[0:2]),
            minute=int(norm_time[2:4]),
            tz="UTC",
        )
        return ts, norm_date, norm_time

    if not _is_missing(raw_datetime):
        try:
            parsed_ts = pd.to_datetime(raw_datetime, utc=True, errors="raise")
            if not pd.isna(parsed_ts):
                derived_date = norm_date or parsed_ts.strftime("%Y-%m-%d")
                derived_time = norm_time or parsed_ts.strftime("%H%M")
                return parsed_ts, derived_date, derived_time
        except (ValueError, TypeError):
            pass

    return pd.NaT, norm_date, norm_time


def _empty_canonical_dataframe(brightness_present: bool = False) -> pd.DataFrame:
    """Create an empty DataFrame with canonical columns and stable dtypes."""
    empty = pd.DataFrame(
        {
            "latitude": pd.Series(dtype="float64"),
            "longitude": pd.Series(dtype="float64"),
            "acq_datetime": pd.Series(dtype="datetime64[ns, UTC]"),
            "acq_date": pd.Series(dtype="object"),
            "acq_time": pd.Series(dtype="object"),
            "sensor": pd.Series(dtype="object"),
            "instrument": pd.Series(dtype="object"),
            "satellite": pd.Series(dtype="object"),
            "confidence": pd.Series(dtype="object"),
            "confidence_norm": pd.Series(dtype="object"),
            "brightness": pd.Series(dtype="float64"),
            "frp": pd.Series(dtype="float64"),
            "scan": pd.Series(dtype="float64"),
            "track": pd.Series(dtype="float64"),
            "daynight": pd.Series(dtype="object"),
            "source_product": pd.Series(dtype="object"),
        }
    )
    empty.attrs["brightness_column_present"] = brightness_present
    empty.attrs["normalized"] = True
    return empty


def _resolve_column_map(columns: pd.Index) -> dict[str, str]:
    """Map canonical target names to actual column names present in DataFrame."""
    lower_to_actual: dict[str, str] = {}
    for col in columns:
        key = str(col).strip().lower()
        if key not in lower_to_actual:
            lower_to_actual[key] = col

    resolved: dict[str, str] = {}
    for target, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_to_actual:
                resolved[target] = lower_to_actual[alias]
                break
    return resolved


def normalize_fields(
    df: pd.DataFrame,
    *,
    source_product: str | None = None,
    sensor: str | None = None,
) -> pd.DataFrame:
    """Normalize raw MODIS or VIIRS FIRMS records into the canonical observation schema.

    Args:
        df: Raw fire detection DataFrame.
        source_product: Optional FIRMS product code (e.g. 'MODIS_SP', 'VIIRS_SNPP_NRT').
        sensor: Optional sensor override ('MODIS' or 'VIIRS').

    Returns:
        Normalized DataFrame with consistent canonical columns and data types.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    explicit_product: str | None = None
    if source_product is not None:
        if not isinstance(source_product, str):
            raise TypeError("source_product must be a string or None.")
        explicit_product = normalize_source_product(source_product)
        if explicit_product is None:
            raise ValueError(
                f"Unsupported source_product {source_product!r}. "
                f"Supported products: {', '.join(sorted(PRODUCTS.keys()))}"
            )

    explicit_sensor: str | None = None
    if sensor is not None:
        if not isinstance(sensor, str):
            raise TypeError("sensor must be a string or None.")
        explicit_sensor = normalize_sensor_name(sensor)
        if explicit_sensor is None:
            raise ValueError(
                f"Unsupported sensor {sensor!r}. Expected 'MODIS' or 'VIIRS'."
            )

    if explicit_product is not None and explicit_sensor is not None:
        prod_sensor = PRODUCT_METADATA[explicit_product]["sensor"]
        if prod_sensor != explicit_sensor:
            raise ValueError(
                f"source_product {explicit_product!r} ({prod_sensor}) conflicts with "
                f"sensor={explicit_sensor!r}."
            )

    col_map = _resolve_column_map(df.columns)
    if df.attrs.get("normalized") and "brightness_column_present" in df.attrs:
        has_brightness_col = bool(df.attrs["brightness_column_present"])
    else:
        has_brightness_col = "brightness" in col_map or "bright_ti4" in col_map

    if df.empty:
        return _empty_canonical_dataframe(brightness_present=has_brightness_col)

    n_rows = len(df)

    # Numeric columns: safe conversion without crashing on malformed strings
    lat_series = (
        pd.to_numeric(df[col_map["latitude"]], errors="coerce").astype("float64")
        if "latitude" in col_map
        else pd.Series(np.nan, index=df.index, dtype="float64")
    )
    lon_series = (
        pd.to_numeric(df[col_map["longitude"]], errors="coerce").astype("float64")
        if "longitude" in col_map
        else pd.Series(np.nan, index=df.index, dtype="float64")
    )
    frp_series = (
        pd.to_numeric(df[col_map["frp"]], errors="coerce").astype("float64")
        if "frp" in col_map
        else pd.Series(np.nan, index=df.index, dtype="float64")
    )
    scan_series = (
        pd.to_numeric(df[col_map["scan"]], errors="coerce").astype("float64")
        if "scan" in col_map
        else pd.Series(np.nan, index=df.index, dtype="float64")
    )
    track_series = (
        pd.to_numeric(df[col_map["track"]], errors="coerce").astype("float64")
        if "track" in col_map
        else pd.Series(np.nan, index=df.index, dtype="float64")
    )

    # Brightness: prefer 'brightness' (MODIS), fallback to 'bright_ti4' (VIIRS)
    if "brightness" in col_map and "bright_ti4" in col_map:
        b_primary = pd.to_numeric(df[col_map["brightness"]], errors="coerce")
        b_viirs = pd.to_numeric(df[col_map["bright_ti4"]], errors="coerce")
        brightness_series = b_primary.combine_first(b_viirs).astype("float64")
    elif "brightness" in col_map:
        brightness_series = pd.to_numeric(
            df[col_map["brightness"]], errors="coerce"
        ).astype("float64")
    elif "bright_ti4" in col_map:
        brightness_series = pd.to_numeric(
            df[col_map["bright_ti4"]], errors="coerce"
        ).astype("float64")
    else:
        brightness_series = pd.Series(np.nan, index=df.index, dtype="float64")

    raw_dates = df[col_map["acq_date"]].tolist() if "acq_date" in col_map else [None] * n_rows
    raw_times = df[col_map["acq_time"]].tolist() if "acq_time" in col_map else [None] * n_rows
    raw_datetimes = (
        df[col_map["acq_datetime"]].tolist() if "acq_datetime" in col_map else [None] * n_rows
    )
    raw_sensors = df[col_map["sensor"]].tolist() if "sensor" in col_map else [None] * n_rows
    raw_satellites = (
        df[col_map["satellite"]].tolist() if "satellite" in col_map else [None] * n_rows
    )
    raw_confidences = (
        df[col_map["confidence"]].tolist() if "confidence" in col_map else [None] * n_rows
    )
    raw_daynights = (
        df[col_map["daynight"]].tolist() if "daynight" in col_map else [None] * n_rows
    )
    raw_products = (
        df[col_map["source_product"]].tolist()
        if "source_product" in col_map
        else [None] * n_rows
    )

    acq_datetimes: list[pd.Timestamp | pd.NaT] = []
    acq_dates: list[str | None] = []
    acq_times: list[str | None] = []
    sensors: list[str | None] = []
    satellites: list[str | None] = []
    confidences_raw: list[Any] = []
    confidences_norm: list[str | None] = []
    daynights: list[str | None] = []
    source_products: list[str | None] = []

    for i in range(n_rows):
        # 1. Timestamp normalization
        ts, norm_date, norm_time = _parse_row_timestamp(
            raw_dates[i], raw_times[i], raw_datetimes[i]
        )
        acq_datetimes.append(ts)
        acq_dates.append(norm_date)
        acq_times.append(norm_time)

        # 2. Source product normalization (preserve raw if unknown so QC can flag it)
        row_prod_raw = raw_products[i]
        if explicit_product is not None:
            row_product = explicit_product
            prod_valid = True
        elif not _is_missing(row_prod_raw):
            norm_prod = normalize_source_product(row_prod_raw)
            if norm_prod is not None:
                row_product = norm_prod
                prod_valid = True
            else:
                row_product = str(row_prod_raw).strip()
                prod_valid = False
        else:
            row_product = None
            prod_valid = True

        # 3. Satellite normalization
        row_sat_raw = raw_satellites[i]
        sat_missing = _is_missing(row_sat_raw)
        mapped_sat, sat_inferred_sensor = normalize_satellite_name(row_sat_raw)

        if sat_missing and prod_valid and row_product is not None:
            platform = PRODUCT_METADATA[row_product]["platform"]
            if platform in ("Suomi-NPP", "NOAA-20", "NOAA-21"):
                mapped_sat = platform
                sat_inferred_sensor = "VIIRS"

        # 4. Sensor normalization
        row_sensor_raw = raw_sensors[i]
        sensor_missing = _is_missing(row_sensor_raw)
        if explicit_sensor is not None:
            row_sensor = explicit_sensor
        elif not sensor_missing:
            row_sensor = normalize_sensor_name(row_sensor_raw)
        elif prod_valid and row_product is not None:
            row_sensor = PRODUCT_METADATA[row_product]["sensor"]
        elif not prod_valid:
            # Explicit source_product column had an unrecognized value
            row_sensor = None
        else:
            row_sensor = sat_inferred_sensor

        # 5. Confidence normalization (sensor-specific scale)
        raw_conf, norm_conf = normalize_confidence(raw_confidences[i], row_sensor)

        # 6. Day/night normalization (preserve unrecognized non-empty value for QC)
        raw_dn = raw_daynights[i]
        if _is_missing(raw_dn):
            norm_dn = None
        else:
            dn_str = str(raw_dn).strip()
            norm_dn = DAYNIGHT_MAPPING.get(dn_str.lower(), dn_str)

        sensors.append(row_sensor)
        satellites.append(mapped_sat)
        confidences_raw.append(raw_conf)
        confidences_norm.append(norm_conf)
        daynights.append(norm_dn)
        source_products.append(row_product)

    result = pd.DataFrame(
        {
            "latitude": lat_series,
            "longitude": lon_series,
            "acq_datetime": pd.Series(
                acq_datetimes, index=df.index, dtype="datetime64[ns, UTC]"
            ),
            "acq_date": pd.Series(acq_dates, index=df.index, dtype="object"),
            "acq_time": pd.Series(acq_times, index=df.index, dtype="object"),
            "sensor": pd.Series(sensors, index=df.index, dtype="object"),
            "instrument": pd.Series(sensors, index=df.index, dtype="object"),
            "satellite": pd.Series(satellites, index=df.index, dtype="object"),
            "confidence": pd.Series(confidences_raw, index=df.index, dtype="object"),
            "confidence_norm": pd.Series(confidences_norm, index=df.index, dtype="object"),
            "brightness": brightness_series,
            "frp": frp_series,
            "scan": scan_series,
            "track": track_series,
            "daynight": pd.Series(daynights, index=df.index, dtype="object"),
            "source_product": pd.Series(source_products, index=df.index, dtype="object"),
        },
        index=df.index,
    )
    result.attrs["brightness_column_present"] = has_brightness_col
    result.attrs["normalized"] = True
    return result
