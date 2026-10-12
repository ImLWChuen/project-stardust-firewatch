"""End-to-end offline integration tests for the NASA FIRMS pipeline (Step 5)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from pipeline.connectors.firms.client import FIRMSClient
from pipeline.connectors.firms.downloader import FIRMSDownloader
from pipeline.connectors.firms.parser import FIRMSAPIError
from pipeline.jobs.daily_update import (
    build_arg_parser,
    run_firms_pipeline,
)
from pipeline.jobs.daily_update import (
    main as daily_update_main,
)
from pipeline.jobs.rebuild_region import (
    main as rebuild_region_main,
)
from pipeline.jobs.rebuild_region import (
    rebuild_region,
)
from pipeline.transformation.aggregate_daily import FIRE_CELL_DAY_COLUMNS
from science.harmonization.canonicalization import (
    canonicalize_fire_dataframe,
    canonicalize_observation,
)

MODIS_CSV_HEADER = (
    "latitude,longitude,brightness,scan,track,acq_date,acq_time,"
    "satellite,confidence,version,bright_t31,frp,daynight"
)
VIIRS_CSV_HEADER = (
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,"
    "satellite,confidence,version,bright_ti5,frp,daynight"
)


class _StubProductClient(FIRMSClient):
    """Offline stub client returning canned CSV payloads per product."""

    def __init__(self, payloads_by_product: dict[str, str | Exception]) -> None:
        super().__init__(map_key="test_offline_key")
        self.payloads_by_product = payloads_by_product
        self.calls: list[tuple[str, str, int, str | None]] = []

    async def fetch_area_csv(
        self,
        source: str,
        bbox: str | list[float],
        day_range: int = 1,
        date: str | None = None,
    ) -> str:
        self.calls.append((source, str(bbox), day_range, date))
        payload = self.payloads_by_product.get(source, "")
        if isinstance(payload, Exception):
            raise payload
        return payload


def test_canonicalization_noaa20_and_noaa21_mapping() -> None:
    rec_n20 = canonicalize_observation(
        {
            "latitude": 4.5,
            "longitude": 101.5,
            "acq_date": "2025-01-15",
            "acq_time": 530,
            "satellite": "NOAA-20",
            "confidence": "n",
            "frp": 14.5,
            "daynight": "D",
        }
    )
    assert rec_n20["satellite"] == "NOAA-20"
    assert rec_n20["instrument"] == "VIIRS"
    assert rec_n20["sensor"] == "VIIRS"
    assert rec_n20["confidence_norm"] == "nominal"
    assert rec_n20["acq_time"] == "0530"

    rec_n21 = canonicalize_observation(
        {
            "latitude": 4.6,
            "longitude": 101.6,
            "acq_date": "2025-01-15",
            "acq_time": "1845",
            "satellite": "NOAA-21",
            "confidence": "h",
            "frp": 28.0,
            "daynight": "N",
        }
    )
    assert rec_n21["satellite"] == "NOAA-21"
    assert rec_n21["instrument"] == "VIIRS"
    assert rec_n21["sensor"] == "VIIRS"
    assert rec_n21["confidence_norm"] == "high"

    assert rec_n20["daynight"] == "D"
    assert rec_n21["daynight"] == "N"

    rec_day = canonicalize_observation({"daynight": "day", "latitude": 1.0, "longitude": 100.0})
    rec_night = canonicalize_observation({"daynight": "night", "latitude": 1.0, "longitude": 100.0})
    rec_none = canonicalize_observation({"daynight": None, "latitude": 1.0, "longitude": 100.0})
    rec_missing = canonicalize_observation({"latitude": 1.0, "longitude": 100.0})
    assert rec_day["daynight"] == "D"
    assert rec_night["daynight"] == "N"
    assert rec_none["daynight"] is None
    assert rec_missing["daynight"] is None

    df = pd.DataFrame([rec_n20, rec_n21])
    norm_df = canonicalize_fire_dataframe(df)
    assert norm_df["sensor"].tolist() == ["VIIRS", "VIIRS"]
    assert norm_df["satellite"].tolist() == ["NOAA-20", "NOAA-21"]


def test_end_to_end_pipeline_modis_viirs_and_rejected_rows(tmp_path: Path) -> None:
    # MODIS_SP has:
    # - 2 valid Terra detections in cell_5.12_100.41 separated by 10 min (03:30 and 03:40) -> deduplicated to 1
    # - 1 invalid row with negative FRP (-5.0) -> rejected with 'invalid_frp'
    modis_csv = (
        f"{MODIS_CSV_HEADER}\n"
        "5.1210,100.4110,325.0,1.0,1.0,2025-01-02,0330,Terra,85,6.11,298.0,20.0,D\n"
        "5.1220,100.4120,328.0,1.0,1.0,2025-01-02,0340,Terra,90,6.11,299.0,25.0,D\n"
        "5.1230,100.4130,320.0,1.0,1.0,2025-01-02,0400,Aqua,75,6.11,295.0,-5.0,D"
    )

    # VIIRS_SNPP_SP has:
    # - 1 valid Suomi-NPP detection in the same cell_5.12_100.41 at 03:35 (preserved as cross-sensor!)
    # - 1 invalid coordinate row (latitude 95.0) -> rejected with 'latitude_out_of_range'
    viirs_snpp_csv = (
        f"{VIIRS_CSV_HEADER}\n"
        "5.1215,100.4115,345.0,0.4,0.4,2025-01-02,0335,N,h,2.0,305.0,30.0,D\n"
        "95.0000,100.4115,345.0,0.4,0.4,2025-01-02,0335,N,n,2.0,305.0,15.0,D"
    )

    # VIIRS_NOAA20_SP has:
    # - 1 valid NOAA-20 detection in a second cell_4.50_101.80 with low confidence ('l') -> retained!
    viirs_noaa20_csv = (
        f"{VIIRS_CSV_HEADER}\n"
        "4.5010,101.8020,335.0,0.4,0.4,2025-01-03,0615,1,l,2.0,300.0,12.5,D"
    )

    stub_client = _StubProductClient(
        {
            "MODIS_SP": modis_csv,
            "VIIRS_SNPP_SP": viirs_snpp_csv,
            "VIIRS_NOAA20_SP": viirs_noaa20_csv,
        }
    )

    raw_dir = tmp_path / "raw"
    interim_dir = tmp_path / "interim"
    processed_dir = tmp_path / "processed"
    downloader = FIRMSDownloader(client=stub_client, dest_dir=str(raw_dir / "malaysia"))

    result = run_firms_pipeline(
        region="malaysia",
        start_date="2025-01-01",
        end_date="2025-01-05",
        mode="sp",
        sensor="all",
        raw_dir=raw_dir,
        interim_dir=interim_dir,
        processed_dir=processed_dir,
        client=stub_client,
        downloader=downloader,
    )

    meta = result["metadata"]
    assert meta["status"] == "completed"
    assert meta["region"] == "malaysia"
    assert meta["products"] == ["MODIS_SP", "VIIRS_SNPP_SP", "VIIRS_NOAA20_SP"]
    assert meta["grid_resolution_deg"] == pytest.approx(0.01)
    assert meta["temporal_dedup_window_minutes"] == pytest.approx(20.0)

    counts = meta["counts"]
    assert counts["raw_total"] == 6
    assert counts["valid_total"] == 4
    assert counts["rejected_total"] == 2
    assert counts["deduplicated_total"] == 3
    assert counts["duplicates_removed"] == 1
    assert counts["fire_cell_day_total"] == 2
    assert counts["rejection_counts"] == {
        "invalid_frp": 1,
        "latitude_out_of_range": 1,
    }

    # Verify raw files were preserved unchanged
    raw_paths = [Path(p) for p in meta["output_paths"]["raw_csv_paths"]]
    assert len(raw_paths) == 3
    assert all(p.is_file() for p in raw_paths)
    assert raw_paths[0].read_text(encoding="utf-8").strip() == modis_csv.strip()

    # Verify interim and processed files exist on disk
    norm_path = Path(meta["output_paths"]["normalized_observations_path"])
    dedup_path = Path(meta["output_paths"]["deduplicated_observations_path"])
    rej_path = Path(meta["output_paths"]["rejected_observations_path"])
    fcd_path = Path(meta["output_paths"]["fire_cell_day_path"])
    meta_path = Path(meta["output_paths"]["metadata_path"])

    for p in (norm_path, dedup_path, rej_path, fcd_path, meta_path):
        assert p.is_file()

    # Verify metadata JSON on disk matches returned metadata
    saved_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert saved_meta == meta

    # Verify FireCellDay content and deterministic ordering by (date, cell_id)
    fcd_df = result["fire_cell_day_df"]
    assert tuple(fcd_df.columns) == FIRE_CELL_DAY_COLUMNS
    assert len(fcd_df) == 2

    row0 = fcd_df.iloc[0]
    assert row0["date"] == "2025-01-02"
    assert row0["cell_id"] == "cell_5.12_100.41"
    assert row0["raw_count"] == 2
    assert row0["modis_count"] == 1
    assert row0["viirs_count"] == 1
    assert row0["raw_frp_sum"] == pytest.approx(50.0)  # 20.0 (MODIS anchor) + 30.0 (VIIRS)
    assert row0["raw_frp_mean"] == pytest.approx(25.0)
    assert row0["sensors_present"] == ["MODIS", "VIIRS"]

    row1 = fcd_df.iloc[1]
    assert row1["date"] == "2025-01-03"
    assert row1["cell_id"] == "cell_4.50_101.80"
    assert row1["raw_count"] == 1
    assert row1["modis_count"] == 0
    assert row1["viirs_count"] == 1
    assert row1["raw_frp_sum"] == pytest.approx(12.5)
    assert row1["sensors_present"] == ["VIIRS"]


def test_pipeline_with_empty_product_and_nrt_noaa21(tmp_path: Path) -> None:
    # Test NRT mode where MODIS_NRT, VIIRS_SNPP_NRT, VIIRS_NOAA20_NRT are empty (header-only)
    # and only VIIRS_NOAA21_NRT has a detection
    noaa21_csv = (
        f"{VIIRS_CSV_HEADER}\n"
        "2.1040,103.2510,350.0,0.4,0.4,2025-01-02,1915,2,n,2.0NRT,304.0,19.5,N"
    )
    stub_client = _StubProductClient(
        {
            "MODIS_NRT": MODIS_CSV_HEADER,
            "VIIRS_SNPP_NRT": "",
            "VIIRS_NOAA20_NRT": VIIRS_CSV_HEADER,
            "VIIRS_NOAA21_NRT": noaa21_csv,
        }
    )

    raw_dir = tmp_path / "raw"
    downloader = FIRMSDownloader(client=stub_client, dest_dir=str(raw_dir / "malaysia"))
    result = run_firms_pipeline(
        region="malaysia",
        start_date="2025-01-01",
        end_date="2025-01-03",
        mode="nrt",
        sensor="all",
        raw_dir=raw_dir,
        interim_dir=tmp_path / "interim",
        processed_dir=tmp_path / "processed",
        client=stub_client,
        downloader=downloader,
    )

    norm_df = result["normalized_df"]
    assert len(norm_df) == 1
    assert norm_df.loc[0, "satellite"] == "NOAA-21"
    assert norm_df.loc[0, "sensor"] == "VIIRS"
    assert norm_df.loc[0, "source_product"] == "VIIRS_NOAA21_NRT"

    fcd_df = result["fire_cell_day_df"]
    assert len(fcd_df) == 1
    assert fcd_df.loc[0, "viirs_count"] == 1
    assert fcd_df.loc[0, "modis_count"] == 0
    assert fcd_df.loc[0, "sensors_present"] == ["VIIRS"]


def test_pipeline_fails_fast_when_one_product_fails(tmp_path: Path) -> None:
    modis_csv = (
        f"{MODIS_CSV_HEADER}\n"
        "5.1210,100.4110,325.0,1.0,1.0,2025-01-02,0330,Terra,85,6.11,298.0,20.0,D"
    )
    stub_client = _StubProductClient(
        {
            "MODIS_SP": modis_csv,
            "VIIRS_SNPP_SP": FIRMSAPIError("FIRMS API returned an error response: Exceeding allowed transaction limit."),
            "VIIRS_NOAA20_SP": VIIRS_CSV_HEADER,
        }
    )
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    downloader = FIRMSDownloader(client=stub_client, dest_dir=str(raw_dir / "malaysia"))

    with pytest.raises(FIRMSAPIError, match="Exceeding allowed transaction limit"):
        run_firms_pipeline(
            region="malaysia",
            start_date="2025-01-01",
            end_date="2025-01-03",
            mode="sp",
            raw_dir=raw_dir,
            interim_dir=tmp_path / "interim",
            processed_dir=processed_dir,
            client=stub_client,
            downloader=downloader,
        )

    # Ensure no run_metadata JSON claiming completion was written
    assert not list(processed_dir.rglob("*run_metadata*.json"))


def test_pipeline_missing_key_invalid_dates_and_cli_help(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)

    # Missing region/bbox must fail rather than defaulting to a global download
    with pytest.raises(ValueError, match="Explicit 'region' or 'bbox' must be provided"):
        run_firms_pipeline(start_date="2025-01-01", end_date="2025-01-03")

    # End date before start date must fail clearly
    with pytest.raises(ValueError, match="must be on or after start_date"):
        rebuild_region(
            "malaysia",
            start_date="2025-01-05",
            end_date="2025-01-01",
        )

    # Missing API key must fail before any network download
    with pytest.raises(ValueError, match="FIRMS_MAP_KEY"):
        run_firms_pipeline(
            region="malaysia",
            start_date="2025-01-01",
            end_date="2025-01-03",
        )

    # CLI --help works without FIRMS_MAP_KEY
    parser = build_arg_parser()
    assert parser.prog == "python -m pipeline.jobs.daily_update"

    with pytest.raises(SystemExit) as exc_daily:
        daily_update_main(["--help"])
    assert exc_daily.value.code == 0

    with pytest.raises(SystemExit) as exc_rebuild:
        rebuild_region_main(["--help"])
    assert exc_rebuild.value.code == 0
