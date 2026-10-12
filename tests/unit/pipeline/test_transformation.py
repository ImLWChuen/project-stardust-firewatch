"""Unit tests for spatial gridding, temporal deduplication, and FireCellDay aggregation."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline.transformation.aggregate_daily import (
    FIRE_CELL_DAY_COLUMNS,
    aggregate_daily,
)
from pipeline.transformation.build_fire_cell_day import build_fire_cell_day
from pipeline.transformation.spatial_grid import grid_observations
from pipeline.transformation.temporal_dedup import deduplicate_observations
from science.harmonization.activity_index import calculate_activity_index
from science.harmonization.config import (
    get_configured_dedup_window_minutes,
    get_configured_grid_resolution,
)
from science.harmonization.spatial_normalization import (
    assign_grid_cell,
    format_cell_id,
)


def test_activity_index_calculation() -> None:
    val = calculate_activity_index(10, 50.0, weight_frp=0.5)
    assert val == 30.0


def test_configured_harmonization_defaults(tmp_path: Path) -> None:
    assert get_configured_grid_resolution() == pytest.approx(0.01)
    dedup_val = get_configured_dedup_window_minutes()
    assert dedup_val == 20.0
    assert isinstance(dedup_val, float)

    # Fractional deduplication window preservation
    custom_cfg = tmp_path / "harmonization_custom.yaml"
    custom_cfg.write_text("harmonization:\n  temporal_dedup_window_minutes: 15.5\n", encoding="utf-8")
    assert get_configured_dedup_window_minutes(custom_cfg) == 15.5


def test_grid_boundaries_and_stable_cell_ids() -> None:
    # Points within the same 0.01-deg cell map to the exact same center and cell_id
    lat1, lon1 = assign_grid_cell(5.1210, 100.5680)
    lat2, lon2 = assign_grid_cell(5.1249, 100.5740)
    assert (lat1, lon1) == (5.12, 100.57)
    assert (lat2, lon2) == (5.12, 100.57)
    assert format_cell_id(lat1, lon1) == "cell_5.12_100.57"

    # Negative coordinates and near-zero coordinates (-0.0 normalized to 0.00)
    z_lat, z_lon = assign_grid_cell(-0.001, 0.002)
    assert (z_lat, z_lon) == (0.0, 0.0)
    assert format_cell_id(z_lat, z_lon) == "cell_0.00_0.00"

    neg_lat, neg_lon = assign_grid_cell(-1.253, -60.418)
    assert (neg_lat, neg_lon) == (-1.25, -60.42)
    assert format_cell_id(neg_lat, neg_lon) == "cell_-1.25_-60.42"


def test_grid_observations_invalid_coordinates() -> None:
    bad_df = pd.DataFrame(
        [
            {"latitude": 5.12, "longitude": 100.57},
            {"latitude": 92.0, "longitude": 100.57},
            {"latitude": np.nan, "longitude": 100.57},
        ]
    )

    with pytest.raises(ValueError, match="missing or out-of-range coordinates"):
        grid_observations(bad_df)

    # Explicit opt-in dropping of invalid coordinate rows
    cleaned = grid_observations(bad_df, drop_invalid_coords=True)
    assert len(cleaned) == 1
    assert cleaned.loc[0, "cell_id"] == "cell_5.12_100.57"

    with pytest.raises(ValueError, match="out of valid range"):
        assign_grid_cell(5.0, -185.0)


def test_temporal_dedup_less_equal_and_greater_than_20_minutes() -> None:
    # Same cell and same sensor:
    # t=05:00 (anchor, frp=10)
    # t=05:12 (delta=12 < 20 -> duplicate, dropped)
    # t=05:20 (delta=20 == 20 -> duplicate at exact window boundary, dropped)
    # t=05:21 (delta=21 > 20 -> distinct detection, kept as new anchor)
    # t=05:35 (delta=14 from 05:21 < 20 -> duplicate of 05:21, dropped)
    df = pd.DataFrame(
        [
            {
                "latitude": 5.121,
                "longitude": 100.571,
                "acq_date": "2025-01-15",
                "acq_time": "0500",
                "sensor": "MODIS",
                "frp": 10.0,
            },
            {
                "latitude": 5.122,
                "longitude": 100.572,
                "acq_date": "2025-01-15",
                "acq_time": "0512",
                "sensor": "MODIS",
                "frp": 15.0,
            },
            {
                "latitude": 5.123,
                "longitude": 100.573,
                "acq_date": "2025-01-15",
                "acq_time": "0520",
                "sensor": "MODIS",
                "frp": 20.0,
            },
            {
                "latitude": 5.121,
                "longitude": 100.571,
                "acq_date": "2025-01-15",
                "acq_time": "0521",
                "sensor": "MODIS",
                "frp": 30.0,
            },
            {
                "latitude": 5.124,
                "longitude": 100.574,
                "acq_date": "2025-01-15",
                "acq_time": "0535",
                "sensor": "MODIS",
                "frp": 25.0,
            },
        ]
    )

    deduped = deduplicate_observations(df)
    assert len(deduped) == 2
    assert deduped["acq_time"].tolist() == ["0500", "0521"]
    assert deduped["frp"].tolist() == [10.0, 30.0]


def test_temporal_dedup_utc_midnight_crossing() -> None:
    # Two MODIS detections in the same cell 15 minutes apart across UTC midnight:
    # 2025-01-15 23:50 UTC and 2025-01-16 00:05 UTC (delta = 15 min <= 20 min)
    # Plus a third detection at 2025-01-16 00:20 UTC (delta from 23:50 is 30 min > 20 min)
    df = pd.DataFrame(
        [
            {
                "latitude": 3.101,
                "longitude": 101.501,
                "acq_date": "2025-01-15",
                "acq_time": "2350",
                "sensor": "MODIS",
                "frp": 18.0,
            },
            {
                "latitude": 3.102,
                "longitude": 101.502,
                "acq_date": "2025-01-16",
                "acq_time": "0005",
                "sensor": "MODIS",
                "frp": 22.0,
            },
            {
                "latitude": 3.101,
                "longitude": 101.501,
                "acq_date": "2025-01-16",
                "acq_time": "0020",
                "sensor": "MODIS",
                "frp": 25.0,
            },
        ]
    )

    deduped = deduplicate_observations(df)
    assert len(deduped) == 2
    assert deduped["acq_date"].tolist() == ["2025-01-15", "2025-01-16"]
    assert deduped["acq_time"].tolist() == ["2350", "0020"]


def test_same_sensor_vs_cross_sensor_deduplication_and_aggregation() -> None:
    # Same cell on 2025-01-15:
    # - Two MODIS detections 10 min apart (06:00 and 06:10) -> deduplicated to 1 MODIS (frp=20.0)
    # - One VIIRS detection 5 min later (06:05) -> preserved because it is VIIRS (frp=30.0)
    # - One VIIRS detection 2 hours later (08:05) -> preserved because delta > 20 min (frp=10.0)
    df = pd.DataFrame(
        [
            {
                "latitude": 4.501,
                "longitude": 102.101,
                "acq_date": "2025-01-15",
                "acq_time": "0600",
                "sensor": "MODIS",
                "satellite": "Terra",
                "confidence": 80,
                "frp": 20.0,
            },
            {
                "latitude": 4.502,
                "longitude": 102.102,
                "acq_date": "2025-01-15",
                "acq_time": "0610",
                "sensor": "MODIS",
                "satellite": "Terra",
                "confidence": 85,
                "frp": 24.0,
            },
            {
                "latitude": 4.501,
                "longitude": 102.101,
                "acq_date": "2025-01-15",
                "acq_time": "0605",
                "sensor": "VIIRS",
                "satellite": "Suomi-NPP",
                "confidence": "h",
                "frp": 30.0,
            },
            {
                "latitude": 4.503,
                "longitude": 102.103,
                "acq_date": "2025-01-15",
                "acq_time": "0805",
                "sensor": "VIIRS",
                "satellite": "NOAA-20",
                "confidence": "n",
                "frp": 10.0,
            },
        ]
    )

    cell_day = build_fire_cell_day(df)
    assert tuple(cell_day.columns) == FIRE_CELL_DAY_COLUMNS
    assert len(cell_day) == 1

    row = cell_day.iloc[0]
    assert row["cell_id"] == "cell_4.50_102.10"
    assert row["date"] == "2025-01-15"
    assert row["cell_lat"] == pytest.approx(4.50)
    assert row["cell_lon"] == pytest.approx(102.10)
    assert row["grid_size_deg"] == pytest.approx(0.01)
    assert row["raw_count"] == 3
    assert row["modis_count"] == 1
    assert row["viirs_count"] == 2
    assert row["raw_frp_sum"] == pytest.approx(60.0)
    assert row["raw_frp_mean"] == pytest.approx(20.0)
    assert row["sensors_present"] == ["MODIS", "VIIRS"]


def test_empty_input_and_missing_optional_columns_in_aggregation() -> None:
    empty_result = build_fire_cell_day(pd.DataFrame())
    assert empty_result.empty
    assert tuple(empty_result.columns) == FIRE_CELL_DAY_COLUMNS

    none_result = build_fire_cell_day(None)
    assert none_result.empty
    assert tuple(none_result.columns) == FIRE_CELL_DAY_COLUMNS

    # Minimal DataFrame without sensor, satellite, confidence, brightness, scan, track
    minimal_df = pd.DataFrame(
        [
            {
                "latitude": 1.234,
                "longitude": 110.567,
                "acq_date": "2025-01-20",
                "acq_time": "1200",
                "frp": 15.0,
            },
            {
                "latitude": 1.231,
                "longitude": 110.569,
                "acq_date": "2025-01-20",
                "acq_time": "1300",
                "frp": 25.0,
            },
        ]
    )
    agg = build_fire_cell_day(minimal_df)
    assert len(agg) == 1
    assert agg.loc[0, "raw_count"] == 2
    assert agg.loc[0, "raw_frp_sum"] == pytest.approx(40.0)
    assert agg.loc[0, "raw_frp_mean"] == pytest.approx(20.0)
    assert agg.loc[0, "modis_count"] == 0
    assert agg.loc[0, "viirs_count"] == 0
    assert agg.loc[0, "sensors_present"] == []


def test_fire_cell_day_matches_json_schema_contract() -> None:
    schema_path = (
        Path(__file__).resolve().parents[3]
        / "contracts"
        / "schemas"
        / "fire-cell-day.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    required_cols = tuple(schema["required"])
    property_cols = tuple(schema["properties"].keys())

    df = pd.DataFrame(
        [
            {
                "latitude": 5.91,
                "longitude": 100.41,
                "acq_date": "2025-01-15",
                "acq_time": "0330",
                "satellite": "Terra",
                "frp": 18.4,
            }
        ]
    )
    result = aggregate_daily(df)

    for req_col in required_cols:
        assert req_col in result.columns
    assert tuple(result.columns) == property_cols
    assert str(result["raw_count"].dtype) == "int64"
    assert str(result["modis_count"].dtype) == "int64"
    assert str(result["viirs_count"].dtype) == "int64"
    assert str(result["raw_frp_sum"].dtype) == "float64"
    assert str(result["raw_frp_mean"].dtype) == "float64"
