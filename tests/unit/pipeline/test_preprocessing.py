"""Unit tests for canonical field normalization and quality control (Step 3)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pipeline.preprocessing.clean_modis import clean_modis
from pipeline.preprocessing.clean_viirs import clean_viirs
from pipeline.preprocessing.filter_invalid import (
    QCConfig,
    evaluate_quality_control,
    filter_invalid,
    filter_invalid_rows,
    run_qc_checks,
)
from pipeline.preprocessing.normalize_fields import (
    CANONICAL_COLUMNS,
    normalize_acq_time,
    normalize_confidence,
    normalize_fields,
)


def _sample_modis_raw_df() -> pd.DataFrame:
    """Build a sample raw MODIS DataFrame covering high, nominal, and low confidence rows."""
    return pd.DataFrame(
        [
            {
                "latitude": 5.9123,
                "longitude": 100.4123,
                "brightness": 324.5,
                "scan": 1.1,
                "track": 1.0,
                "acq_date": "2025-01-15",
                "acq_time": 330,
                "satellite": "Terra",
                "confidence": 82,
                "version": "6.11",
                "bright_t31": 298.2,
                "frp": 18.4,
                "daynight": "D",
            },
            {
                "latitude": 5.9451,
                "longitude": 100.4512,
                "brightness": 310.0,
                "scan": 1.2,
                "track": 1.1,
                "acq_date": "2025-01-15",
                "acq_time": "0645",
                "satellite": "A",
                "confidence": 45,
                "version": "6.11",
                "bright_t31": 295.0,
                "frp": 12.0,
                "daynight": "d",
            },
            {
                "latitude": 4.2000,
                "longitude": 101.1000,
                "brightness": 301.2,
                "scan": 1.0,
                "track": 1.0,
                "acq_date": "2025-01-15",
                "acq_time": 5,
                "satellite": "T",
                "confidence": 15,
                "version": "6.11",
                "bright_t31": 290.1,
                "frp": 4.5,
                "daynight": "N",
            },
        ]
    )


def _sample_viirs_raw_df() -> pd.DataFrame:
    """Build a sample raw VIIRS DataFrame covering Suomi-NPP, NOAA-20, and NOAA-21 rows."""
    return pd.DataFrame(
        [
            {
                "latitude": 5.9125,
                "longitude": 100.4121,
                "bright_ti4": 342.1,
                "scan": 0.4,
                "track": 0.4,
                "acq_date": "2025-01-15",
                "acq_time": "0530",
                "satellite": "N",
                "confidence": "l",
                "version": "2.0",
                "bright_ti5": 302.1,
                "frp": 5.2,
                "daynight": "D",
            },
            {
                "latitude": 5.9453,
                "longitude": 100.4510,
                "bright_ti4": 348.7,
                "scan": 0.4,
                "track": 0.4,
                "acq_date": "2025-01-15",
                "acq_time": 1845,
                "satellite": "1",
                "confidence": "n",
                "version": "2.0",
                "bright_ti5": 305.4,
                "frp": 26.5,
                "daynight": "N",
            },
            {
                "latitude": 6.1000,
                "longitude": 100.8000,
                "bright_ti4": 365.0,
                "scan": 0.5,
                "track": 0.4,
                "acq_date": "2025-01-15",
                "acq_time": "1905",
                "satellite": "NOAA-21",
                "confidence": "h",
                "version": "2.0NRT",
                "bright_ti5": 310.0,
                "frp": 42.0,
                "daynight": "N",
            },
        ]
    )


def test_normalize_modis_numeric_confidence_and_fields() -> None:
    """Verify MODIS field normalization maps numeric confidence and canonical fields correctly."""
    raw = _sample_modis_raw_df()
    norm = normalize_fields(raw, source_product="MODIS_SP")

    assert tuple(norm.columns) == CANONICAL_COLUMNS
    assert norm["sensor"].tolist() == ["MODIS", "MODIS", "MODIS"]
    assert norm["instrument"].tolist() == ["MODIS", "MODIS", "MODIS"]
    assert norm["satellite"].tolist() == ["Terra", "Aqua", "Terra"]
    assert norm["confidence"].tolist() == [82, 45, 15]
    assert norm["confidence_norm"].tolist() == ["high", "nominal", "low"]
    assert norm["acq_time"].tolist() == ["0330", "0645", "0005"]
    assert norm["daynight"].tolist() == ["D", "D", "N"]
    assert norm["source_product"].tolist() == ["MODIS_SP", "MODIS_SP", "MODIS_SP"]
    assert norm["brightness"].tolist() == pytest.approx([324.5, 310.0, 301.2])
    assert str(norm["acq_datetime"].dtype) == "datetime64[ns, UTC]"


def test_normalize_viirs_categorical_confidence_and_bright_ti4() -> None:
    """Verify VIIRS field normalization maps categorical confidence and bright_ti4 to brightness correctly."""
    raw = _sample_viirs_raw_df()
    norm = normalize_fields(raw)

    assert tuple(norm.columns) == CANONICAL_COLUMNS
    assert norm["sensor"].tolist() == ["VIIRS", "VIIRS", "VIIRS"]
    assert norm["satellite"].tolist() == ["Suomi-NPP", "NOAA-20", "NOAA-21"]
    assert norm["confidence"].tolist() == ["l", "n", "h"]
    assert norm["confidence_norm"].tolist() == ["low", "nominal", "high"]
    assert norm["brightness"].tolist() == pytest.approx([342.1, 348.7, 365.0])
    assert norm["acq_time"].tolist() == ["0530", "1845", "1905"]
    assert norm["source_product"].tolist() == [None, None, None]


def test_confidence_scales_not_conflated_between_sensors() -> None:
    """Verify MODIS numeric and VIIRS categorical confidence scales are not conflated across sensors."""
    # VIIRS rejects numeric confidence; MODIS rejects categorical letter codes
    assert normalize_confidence("n", "MODIS") == ("n", None)
    assert normalize_confidence(85, "VIIRS") == (85, None)
    assert normalize_confidence(0, "MODIS") == (0, "low")
    assert normalize_confidence(30, "MODIS") == (30, "nominal")
    assert normalize_confidence(80, "MODIS") == (80, "high")
    assert normalize_confidence(100, "MODIS") == (100, "high")
    assert normalize_confidence(105, "MODIS") == (105, None)
    assert normalize_confidence(-1, "MODIS") == (-1, None)
    assert normalize_confidence("nominal", "VIIRS") == ("nominal", "nominal")
    assert normalize_confidence("HIGH", "VIIRS") == ("HIGH", "high")


def test_timestamps_crossing_midnight_and_invalid_timestamps() -> None:
    """Verify timestamps spanning midnight are ordered chronologically and invalid timestamps are rejected."""
    raw = pd.DataFrame(
        [
            {
                "latitude": 1.5,
                "longitude": 103.5,
                "brightness": 320.0,
                "acq_date": "2025-01-15",
                "acq_time": 2358,
                "satellite": "Terra",
                "confidence": 75,
                "frp": 10.0,
            },
            {
                "latitude": 1.51,
                "longitude": 103.51,
                "brightness": 322.0,
                "acq_date": "2025-01-16",
                "acq_time": 0,
                "satellite": "Terra",
                "confidence": 80,
                "frp": 11.0,
            },
            {
                "latitude": 1.52,
                "longitude": 103.52,
                "brightness": 325.0,
                "acq_date": "2025-01-16",
                "acq_time": 3,
                "satellite": "Terra",
                "confidence": 85,
                "frp": 12.0,
            },
            {
                "latitude": 1.53,
                "longitude": 103.53,
                "brightness": 325.0,
                "acq_date": "2025-01-16",
                "acq_time": "2400",
                "satellite": "Terra",
                "confidence": 85,
                "frp": 12.0,
            },
            {
                "latitude": 1.54,
                "longitude": 103.54,
                "brightness": 325.0,
                "acq_date": "2025-02-30",
                "acq_time": "0115",
                "satellite": "Terra",
                "confidence": 85,
                "frp": 12.0,
            },
        ]
    )

    valid_df, rejected_df = filter_invalid_rows(raw, return_rejected=True)
    assert len(valid_df) == 3
    assert len(rejected_df) == 2
    assert valid_df["acq_time"].tolist() == ["2358", "0000", "0003"]

    # Verify chronological difference across midnight is exactly 2 and 5 minutes
    t0, t1, t2 = valid_df["acq_datetime"].tolist()
    assert (t1 - t0).total_seconds() == 120.0
    assert (t2 - t0).total_seconds() == 300.0
    assert all("invalid_timestamp" in r for r in rejected_df["rejection_reason"])
    assert normalize_acq_time("1260") is None


def test_missing_optional_columns_handled_safely() -> None:
    """Verify normalization and QC handle missing optional columns without rejecting valid rows."""
    # Omit brightness/bright_ti4, scan, track, daynight, source_product
    raw = pd.DataFrame(
        [
            {
                "latitude": 3.14,
                "longitude": 101.69,
                "acq_date": "2025-01-20",
                "acq_time": "0415",
                "satellite": "Suomi-NPP",
                "confidence": "n",
                "frp": 14.2,
            }
        ]
    )

    norm = normalize_fields(raw)
    assert tuple(norm.columns) == CANONICAL_COLUMNS
    assert np.isnan(norm.loc[0, "brightness"])
    assert np.isnan(norm.loc[0, "scan"])
    assert np.isnan(norm.loc[0, "track"])
    assert norm.loc[0, "daynight"] is None
    assert norm.loc[0, "source_product"] is None

    # Quality control must not reject rows when optional columns were omitted
    valid_df, rejected_df = filter_invalid_rows(norm, return_rejected=True)
    assert len(valid_df) == 1
    assert len(rejected_df) == 0


def test_qc_coordinates_frp_and_brightness_validation() -> None:
    """Verify quality control rejects out-of-range coordinates, invalid FRP, and invalid brightness."""
    raw = pd.DataFrame(
        [
            # 0: Valid row
            {
                "latitude": 2.5,
                "longitude": 102.5,
                "brightness": 330.0,
                "acq_date": "2025-01-10",
                "acq_time": "0500",
                "satellite": "Terra",
                "confidence": 70,
                "frp": 0.0,
            },
            # 1: Latitude out of range (> 90)
            {
                "latitude": 95.0,
                "longitude": 102.5,
                "brightness": 330.0,
                "acq_date": "2025-01-10",
                "acq_time": "0500",
                "satellite": "Terra",
                "confidence": 70,
                "frp": 10.0,
            },
            # 2: Longitude out of range (< -180)
            {
                "latitude": 2.5,
                "longitude": -181.0,
                "brightness": 330.0,
                "acq_date": "2025-01-10",
                "acq_time": "0500",
                "satellite": "Terra",
                "confidence": 70,
                "frp": 10.0,
            },
            # 3: Unparseable coordinates
            {
                "latitude": "bad_lat",
                "longitude": 102.5,
                "brightness": 330.0,
                "acq_date": "2025-01-10",
                "acq_time": "0500",
                "satellite": "Terra",
                "confidence": 70,
                "frp": 10.0,
            },
            # 4: Negative FRP
            {
                "latitude": 2.5,
                "longitude": 102.5,
                "brightness": 330.0,
                "acq_date": "2025-01-10",
                "acq_time": "0500",
                "satellite": "Terra",
                "confidence": 70,
                "frp": -3.5,
            },
            # 5: Non-numeric FRP
            {
                "latitude": 2.5,
                "longitude": 102.5,
                "brightness": 330.0,
                "acq_date": "2025-01-10",
                "acq_time": "0500",
                "satellite": "Terra",
                "confidence": 70,
                "frp": "not_a_number",
            },
            # 6: Invalid brightness when brightness column is present
            {
                "latitude": 2.5,
                "longitude": 102.5,
                "brightness": -10.0,
                "acq_date": "2025-01-10",
                "acq_time": "0500",
                "satellite": "Terra",
                "confidence": 70,
                "frp": 10.0,
            },
        ]
    )

    report = evaluate_quality_control(raw)
    assert report.total_rows == 7
    assert report.valid_rows == 1
    assert report.rejected_rows == 6
    assert not report.passed

    reasons = report.rejected_df["rejection_reason"].tolist()
    assert reasons[0] == "latitude_out_of_range"
    assert reasons[1] == "longitude_out_of_range"
    assert reasons[2] == "missing_or_invalid_coordinates"
    assert reasons[3] == "invalid_frp"
    assert reasons[4] == "invalid_frp"
    assert reasons[5] == "invalid_brightness"


def test_unknown_sensor_and_product_handling() -> None:
    """Verify unsupported or conflicting sensor/product/satellite combinations are rejected rather than invented."""
    raw = _sample_modis_raw_df()

    with pytest.raises(ValueError, match="Unsupported source_product"):
        normalize_fields(raw, source_product="LANDSAT_FAKE")

    with pytest.raises(ValueError, match="Unsupported sensor"):
        normalize_fields(raw, sensor="AVHRR")

    with pytest.raises(ValueError, match="conflicts with sensor"):
        normalize_fields(raw, source_product="VIIRS_SNPP_NRT", sensor="MODIS")

    # Unknown satellite/sensor/product in DataFrame columns must not be invented
    bad_rows = pd.DataFrame(
        [
            {
                "latitude": 3.0,
                "longitude": 101.0,
                "brightness": 325.0,
                "acq_date": "2025-01-15",
                "acq_time": "0600",
                "satellite": "UnknownSat",
                "confidence": 80,
                "frp": 15.0,
            },
            {
                "latitude": 3.0,
                "longitude": 101.0,
                "brightness": 325.0,
                "acq_date": "2025-01-15",
                "acq_time": "0600",
                "sensor": "MODIS",
                "satellite": "NOAA-20",
                "confidence": 80,
                "frp": 15.0,
            },
        ]
    )
    norm = normalize_fields(bad_rows)
    assert norm.loc[0, "satellite"] is None
    assert norm.loc[0, "sensor"] is None

    valid_df, rejected_df = filter_invalid(norm, return_rejected=True)
    assert len(valid_df) == 0
    assert len(rejected_df) == 2
    assert "invalid_satellite" in rejected_df.loc[0, "rejection_reason"]
    assert "invalid_sensor" in rejected_df.loc[0, "rejection_reason"]
    assert "sensor_satellite_mismatch" in rejected_df.loc[1, "rejection_reason"]


def test_empty_dataframes_and_consistent_dtypes() -> None:
    """Verify empty and cleaned DataFrames always expose the canonical columns with consistent dtypes."""
    empty_raw = pd.DataFrame()
    norm_empty = normalize_fields(empty_raw)
    qc_empty = run_qc_checks(empty_raw)

    modis_clean = clean_modis(_sample_modis_raw_df(), source_product="MODIS_SP")
    viirs_clean = clean_viirs(_sample_viirs_raw_df(), source_product="VIIRS_SNPP_SP")
    # Note: _sample_viirs_raw_df has 1 row for Suomi-NPP, 1 for NOAA-20, 1 for NOAA-21;
    # passing source_product="VIIRS_SNPP_SP" keeps only the Suomi-NPP row!
    assert len(viirs_clean) == 1
    assert viirs_clean.loc[0, "satellite"] == "Suomi-NPP"

    for df in (norm_empty, qc_empty, modis_clean, viirs_clean):
        assert tuple(df.columns) == CANONICAL_COLUMNS
        assert str(df["latitude"].dtype) == "float64"
        assert str(df["longitude"].dtype) == "float64"
        assert str(df["brightness"].dtype) == "float64"
        assert str(df["frp"].dtype) == "float64"
        assert str(df["scan"].dtype) == "float64"
        assert str(df["track"].dtype) == "float64"
        assert str(df["acq_datetime"].dtype) == "datetime64[ns, UTC]"


def test_configurable_low_confidence_filtering() -> None:
    """Verify low-confidence rows are retained by default but rejected when drop_low_confidence is enabled."""
    raw = _sample_modis_raw_df()  # confidences: 82 (high), 45 (nominal), 15 (low)

    # Default retains low confidence
    default_valid = filter_invalid_rows(raw)
    assert len(default_valid) == 3

    # Optional drop_low_confidence=True rejects the low-confidence row
    filtered, rejected = filter_invalid_rows(
        raw, config=QCConfig(drop_low_confidence=True), return_rejected=True
    )
    assert len(filtered) == 2
    assert len(rejected) == 1
    assert rejected.loc[0, "rejection_reason"] == "low_confidence"
