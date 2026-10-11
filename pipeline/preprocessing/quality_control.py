"""Run quality control (QC) checks and filter invalid fire detection records."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from pipeline.connectors.firms.products import PRODUCT_METADATA, PRODUCTS
from pipeline.preprocessing.normalize_fields import (
    CANONICAL_COLUMNS,
    SENSOR_PLATFORMS,
    _is_missing,
    normalize_fields,
)

VALID_CONFIDENCE_NORMS: frozenset[str] = frozenset({"low", "nominal", "high"})
VALID_SATELLITES: frozenset[str] = frozenset(
    {"Terra", "Aqua", "Suomi-NPP", "NOAA-20", "NOAA-21"}
)


@dataclass(frozen=True)
class QCConfig:
    """Configurable quality control rules for normalized fire observations."""

    min_lat: float = -90.0
    max_lat: float = 90.0
    min_lon: float = -180.0
    max_lon: float = 180.0
    min_frp: float = 0.0
    min_brightness: float = 100.0
    max_brightness: float = 600.0
    drop_low_confidence: bool = False
    min_modis_confidence: float | None = None


@dataclass
class QCReport:
    """Structured result of running quality control on a fire observation dataset."""

    valid_df: pd.DataFrame
    rejected_df: pd.DataFrame
    rejection_counts: dict[str, int] = field(default_factory=dict)
    total_rows: int = 0
    valid_rows: int = 0
    rejected_rows: int = 0
    passed: bool = True


def _validate_row(
    *,
    lat: Any,
    lon: Any,
    acq_datetime: Any,
    acq_date: Any,
    acq_time: Any,
    sensor: Any,
    satellite: Any,
    confidence: Any,
    confidence_norm: Any,
    brightness: Any,
    frp: Any,
    scan: Any,
    track: Any,
    daynight: Any,
    source_product: Any,
    brightness_present: bool,
    config: QCConfig,
) -> list[str]:
    """Return a list of rejection reason codes for a single normalized observation row."""
    reasons: list[str] = []

    # 1. Coordinates check
    lat_missing = _is_missing(lat) or not isinstance(lat, (int, float)) or not math.isfinite(float(lat))
    lon_missing = _is_missing(lon) or not isinstance(lon, (int, float)) or not math.isfinite(float(lon))
    if lat_missing or lon_missing:
        reasons.append("missing_or_invalid_coordinates")
    else:
        lat_f = float(lat)
        lon_f = float(lon)
        if lat_f < config.min_lat or lat_f > config.max_lat:
            reasons.append("latitude_out_of_range")
        if lon_f < config.min_lon or lon_f > config.max_lon:
            reasons.append("longitude_out_of_range")

    # 2. Acquisition timestamp check
    if pd.isna(acq_datetime) or _is_missing(acq_date) or _is_missing(acq_time):
        reasons.append("invalid_timestamp")

    # 3. Source product, sensor, and satellite check
    if not _is_missing(source_product):
        prod_str = str(source_product)
        if prod_str not in PRODUCTS:
            reasons.append("invalid_source_product")
        else:
            meta = PRODUCT_METADATA[prod_str]
            if (not _is_missing(sensor) and str(sensor) != meta["sensor"]) or (
                meta["platform"] in ("Suomi-NPP", "NOAA-20", "NOAA-21")
                and not _is_missing(satellite)
                and str(satellite) != meta["platform"]
            ):
                reasons.append("invalid_source_product")

    sensor_valid = not _is_missing(sensor) and str(sensor) in SENSOR_PLATFORMS
    if not sensor_valid:
        reasons.append("invalid_sensor")

    sat_valid = not _is_missing(satellite) and str(satellite) in VALID_SATELLITES
    if not sat_valid:
        reasons.append("invalid_satellite")
    elif sensor_valid and str(satellite) not in SENSOR_PLATFORMS[str(sensor)]:
        reasons.append("sensor_satellite_mismatch")

    # 4. Sensor-specific confidence check
    if _is_missing(confidence_norm) or str(confidence_norm) not in VALID_CONFIDENCE_NORMS:
        reasons.append("invalid_confidence")
    else:
        if config.drop_low_confidence and str(confidence_norm) == "low":
            reasons.append("low_confidence")
        elif (
            sensor_valid
            and str(sensor) == "MODIS"
            and config.min_modis_confidence is not None
        ):
            try:
                if float(confidence) < config.min_modis_confidence:
                    reasons.append("low_confidence")
            except (TypeError, ValueError):
                reasons.append("invalid_confidence")

    # 5. FRP check (required, >= min_frp)
    if (
        _is_missing(frp)
        or not isinstance(frp, (int, float))
        or not math.isfinite(float(frp))
        or float(frp) < config.min_frp
    ):
        reasons.append("invalid_frp")

    # 6. Brightness check (validated when the source brightness field is present)
    if brightness_present:
        if (
            _is_missing(brightness)
            or not isinstance(brightness, (int, float))
            or not math.isfinite(float(brightness))
        ):
            reasons.append("invalid_brightness")
        else:
            b_val = float(brightness)
            if (
                b_val <= 0.0
                or b_val < config.min_brightness
                or b_val > config.max_brightness
            ):
                reasons.append("invalid_brightness")

    # 7. Optional scan, track, and daynight checks when present
    if not _is_missing(scan) and (
        not isinstance(scan, (int, float))
        or not math.isfinite(float(scan))
        or float(scan) <= 0.0
    ):
        reasons.append("invalid_scan_track")
    if (
        not _is_missing(track)
        and "invalid_scan_track" not in reasons
        and (
            not isinstance(track, (int, float))
            or not math.isfinite(float(track))
            or float(track) <= 0.0
        )
    ):
        reasons.append("invalid_scan_track")

    if not _is_missing(daynight) and str(daynight) not in ("D", "N"):
        reasons.append("invalid_daynight")

    return reasons


def _is_already_normalized(
    df: pd.DataFrame,
    source_product: str | None,
    sensor: str | None,
) -> bool:
    """Return True if df already has canonical columns and no overrides were requested."""
    if source_product is not None or sensor is not None:
        return False
    return bool(
        df.attrs.get("normalized") is True
        and all(col in df.columns for col in CANONICAL_COLUMNS)
    )


def evaluate_quality_control(
    df: pd.DataFrame,
    *,
    config: QCConfig | None = None,
    source_product: str | None = None,
    sensor: str | None = None,
    drop_low_confidence: bool | None = None,
    min_modis_confidence: float | None = None,
    min_brightness: float | None = None,
    max_brightness: float | None = None,
) -> QCReport:
    """Normalize (if needed) and evaluate quality control rules on a DataFrame.

    Returns a QCReport containing valid_df, rejected_df (with 'rejection_reason'),
    and summary counts.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    base_cfg = config or QCConfig()
    effective_cfg = QCConfig(
        min_lat=base_cfg.min_lat,
        max_lat=base_cfg.max_lat,
        min_lon=base_cfg.min_lon,
        max_lon=base_cfg.max_lon,
        min_frp=base_cfg.min_frp,
        min_brightness=(
            min_brightness if min_brightness is not None else base_cfg.min_brightness
        ),
        max_brightness=(
            max_brightness if max_brightness is not None else base_cfg.max_brightness
        ),
        drop_low_confidence=(
            drop_low_confidence
            if drop_low_confidence is not None
            else base_cfg.drop_low_confidence
        ),
        min_modis_confidence=(
            min_modis_confidence
            if min_modis_confidence is not None
            else base_cfg.min_modis_confidence
        ),
    )

    if _is_already_normalized(df, source_product, sensor):
        norm_df = df.copy()
        norm_df.attrs.update(df.attrs)
    else:
        norm_df = normalize_fields(df, source_product=source_product, sensor=sensor)

    brightness_present = bool(norm_df.attrs.get("brightness_column_present", False))

    if norm_df.empty:
        rejected_empty = norm_df.copy()
        rejected_empty["rejection_reason"] = pd.Series(dtype="object")
        return QCReport(
            valid_df=norm_df.copy(),
            rejected_df=rejected_empty,
            rejection_counts={},
            total_rows=0,
            valid_rows=0,
            rejected_rows=0,
            passed=True,
        )

    n_rows = len(norm_df)
    lats = norm_df["latitude"].tolist()
    lons = norm_df["longitude"].tolist()
    acq_dts = norm_df["acq_datetime"].tolist()
    acq_dates = norm_df["acq_date"].tolist()
    acq_times = norm_df["acq_time"].tolist()
    sensors = norm_df["sensor"].tolist()
    satellites = norm_df["satellite"].tolist()
    confidences = norm_df["confidence"].tolist()
    confidence_norms = norm_df["confidence_norm"].tolist()
    brightnesses = norm_df["brightness"].tolist()
    frps = norm_df["frp"].tolist()
    scans = norm_df["scan"].tolist()
    tracks = norm_df["track"].tolist()
    daynights = norm_df["daynight"].tolist()
    source_products = norm_df["source_product"].tolist()

    valid_mask: list[bool] = []
    rejection_reasons_col: list[str] = []
    rejection_counts: dict[str, int] = {}

    for i in range(n_rows):
        row_reasons = _validate_row(
            lat=lats[i],
            lon=lons[i],
            acq_datetime=acq_dts[i],
            acq_date=acq_dates[i],
            acq_time=acq_times[i],
            sensor=sensors[i],
            satellite=satellites[i],
            confidence=confidences[i],
            confidence_norm=confidence_norms[i],
            brightness=brightnesses[i],
            frp=frps[i],
            scan=scans[i],
            track=tracks[i],
            daynight=daynights[i],
            source_product=source_products[i],
            brightness_present=brightness_present,
            config=effective_cfg,
        )
        if row_reasons:
            valid_mask.append(False)
            rejection_reasons_col.append(";".join(row_reasons))
            for reason in row_reasons:
                rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
        else:
            valid_mask.append(True)
            rejection_reasons_col.append("")

    mask_series = pd.Series(valid_mask, index=norm_df.index, dtype="bool")
    valid_df = norm_df.loc[mask_series].reset_index(drop=True)
    valid_df.attrs["brightness_column_present"] = brightness_present
    valid_df.attrs["normalized"] = True

    rejected_df = norm_df.loc[~mask_series].copy()
    rejected_df["rejection_reason"] = [
        r for r, is_valid in zip(rejection_reasons_col, valid_mask) if not is_valid
    ]
    rejected_df = rejected_df.reset_index(drop=True)

    return QCReport(
        valid_df=valid_df,
        rejected_df=rejected_df,
        rejection_counts=rejection_counts,
        total_rows=n_rows,
        valid_rows=len(valid_df),
        rejected_rows=len(rejected_df),
        passed=(len(rejected_df) == 0),
    )


def filter_invalid_rows(
    df: pd.DataFrame,
    *,
    config: QCConfig | None = None,
    return_rejected: bool = False,
    source_product: str | None = None,
    sensor: str | None = None,
    drop_low_confidence: bool | None = None,
    min_modis_confidence: float | None = None,
    min_brightness: float | None = None,
    max_brightness: float | None = None,
) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
    """Filter invalid rows from raw or normalized fire observations.

    Args:
        df: Input fire observation DataFrame (raw or normalized).
        config: Optional QCConfig instance.
        return_rejected: If True, return (valid_df, rejected_df) where rejected_df
            includes a 'rejection_reason' column.
        source_product: Optional FIRMS product identifier.
        sensor: Optional sensor override ('MODIS' or 'VIIRS').
        drop_low_confidence: Optional override to drop 'low' confidence detections.
        min_modis_confidence: Optional minimum numeric confidence for MODIS (0-100).
        min_brightness: Optional minimum valid brightness temperature in Kelvin.
        max_brightness: Optional maximum valid brightness temperature in Kelvin.

    Returns:
        Filtered valid DataFrame, or (valid_df, rejected_df) if return_rejected=True.
    """
    report = evaluate_quality_control(
        df,
        config=config,
        source_product=source_product,
        sensor=sensor,
        drop_low_confidence=drop_low_confidence,
        min_modis_confidence=min_modis_confidence,
        min_brightness=min_brightness,
        max_brightness=max_brightness,
    )
    if return_rejected:
        return report.valid_df, report.rejected_df
    return report.valid_df


def run_qc_checks(
    df: pd.DataFrame,
    *,
    config: QCConfig | None = None,
    return_report: bool = False,
    return_rejected: bool = False,
    source_product: str | None = None,
    sensor: str | None = None,
    drop_low_confidence: bool | None = None,
    min_modis_confidence: float | None = None,
    min_brightness: float | None = None,
    max_brightness: float | None = None,
) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame] | QCReport:
    """Run quality control checks on ingested fire observation records.

    Returns the filtered valid DataFrame by default, (valid_df, rejected_df) when
    return_rejected=True, or a full QCReport when return_report=True.
    """
    report = evaluate_quality_control(
        df,
        config=config,
        source_product=source_product,
        sensor=sensor,
        drop_low_confidence=drop_low_confidence,
        min_modis_confidence=min_modis_confidence,
        min_brightness=min_brightness,
        max_brightness=max_brightness,
    )
    if return_report:
        return report
    if return_rejected:
        return report.valid_df, report.rejected_df
    return report.valid_df
