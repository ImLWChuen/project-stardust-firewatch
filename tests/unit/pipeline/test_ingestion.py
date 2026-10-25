from __future__ import annotations

import asyncio
from datetime import date

import httpx
import pytest

from backend.app.core.config import Settings
from backend.app.integrations.firms.client import FIRMSClient as BackendFIRMSClient
from backend.app.integrations.firms.parser import parse_firms_csv
from pipeline.connectors.firms.client import (
    FIRMSAPIError,
    FIRMSClient,
    validate_bbox,
    validate_day_range,
    validate_query_date,
)
from pipeline.connectors.firms.downloader import (
    FIRMSDownloader,
    chunk_date_range,
    combine_csv_chunks,
)
from pipeline.connectors.firms.products import (
    MODIS_NRT,
    MODIS_SP,
    PRODUCTS,
    VIIRS_NOAA20_NRT,
    VIIRS_NOAA20_SP,
    VIIRS_NOAA21_NRT,
    VIIRS_SNPP_NRT,
    VIIRS_SNPP_SP,
    get_products_for_sensor,
    validate_product,
)
from pipeline.ingestion.download_all import (
    build_arg_parser as build_all_parser,
)
from pipeline.ingestion.download_all import (
    download_all,
    get_pipeline_data_dirs,
    load_regions_config,
    resolve_region_bbox,
)
from pipeline.ingestion.download_modis import (
    build_arg_parser as build_modis_parser,
)
from pipeline.ingestion.download_modis import (
    download_modis_data,
)
from pipeline.ingestion.download_viirs import (
    build_arg_parser as build_viirs_parser,
)
from pipeline.ingestion.download_viirs import (
    download_viirs_data,
)

CSV_HEADER = (
    "latitude,longitude,brightness,scan,track,acq_date,acq_time,"
    "satellite,confidence,version,bright_t31,frp,daynight"
)
CSV_ROW_1 = "5.1,100.2,312.4,1.0,1.0,2025-01-01,0630,Terra,85,6.1,295.1,15.2,D"
CSV_ROW_2 = "5.8,100.6,320.1,1.1,1.0,2025-01-06,0715,Aqua,90,6.1,298.0,22.4,D"


def test_parse_firms():
    """Verify a single-row FIRMS CSV sample parses into the expected DataFrame."""
    csv_sample = "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,confidence,version,bright_t31,frp,daynight\n5.1,100.2,312.4,1.0,1.0,2026-03-01,0630,Terra,85,6.1NRT,295.1,15.2,D"
    df = parse_firms_csv(csv_sample)
    assert len(df) == 1
    assert df.iloc[0]["latitude"] == 5.1


def test_parse_firms_empty_and_header_only():
    """Verify parsing empty, whitespace-only, and header-only CSV text returns empty DataFrames."""
    empty_df = parse_firms_csv("")
    assert empty_df.empty
    assert "latitude" in empty_df.columns
    assert "longitude" in empty_df.columns

    whitespace_df = parse_firms_csv("   \n  ")
    assert whitespace_df.empty

    header_only_df = parse_firms_csv(f"{CSV_HEADER}\n")
    assert header_only_df.empty
    assert list(header_only_df.columns) == CSV_HEADER.split(",")


@pytest.mark.parametrize(
    "error_body",
    [
        "Invalid MAP_KEY.",
        "Invalid area coordinates specified.",
        "Error: day_range must be between 1 and 5",
        "Exceeding allowed transaction limit.",
        "<!DOCTYPE html><html><body>503 Service Unavailable</body></html>",
        "foo,bar,baz\n1,2,3",
    ],
)
def test_parse_firms_rejects_plain_text_errors(error_body: str):
    """Verify non-CSV error response bodies raise FIRMSAPIError instead of being parsed."""
    with pytest.raises(FIRMSAPIError):
        parse_firms_csv(error_body)


def test_products_sp_vs_nrt_and_no_invented_noaa21_sp():
    """Verify SP/NRT product selection per sensor and that no fictitious NOAA-21 SP product exists."""
    assert "VIIRS_NOAA21_SP" not in PRODUCTS
    with pytest.raises(ValueError, match="Unsupported FIRMS product"):
        validate_product("VIIRS_NOAA21_SP")

    assert get_products_for_sensor("modis", "nrt") == [MODIS_NRT]
    assert get_products_for_sensor("modis", "sp") == [MODIS_SP]
    assert get_products_for_sensor("viirs", "nrt") == [
        VIIRS_SNPP_NRT,
        VIIRS_NOAA20_NRT,
        VIIRS_NOAA21_NRT,
    ]
    assert get_products_for_sensor("viirs", "sp") == [
        VIIRS_SNPP_SP,
        VIIRS_NOAA20_SP,
    ]
    assert get_products_for_sensor("all", "sp") == [
        MODIS_SP,
        VIIRS_SNPP_SP,
        VIIRS_NOAA20_SP,
    ]
    with pytest.raises(ValueError, match="NOAA-21"):
        get_products_for_sensor("noaa21", "sp")


def test_validate_day_range():
    """Verify day_range validation accepts 1-5 and rejects out-of-range values and wrong types."""
    for valid_days in (1, 2, 3, 4, 5):
        assert validate_day_range(valid_days) == valid_days

    for invalid_days in (0, 6, 10, -1):
        with pytest.raises(ValueError):
            validate_day_range(invalid_days)

    for invalid_type in (True, "3", 2.5):
        with pytest.raises(TypeError):
            validate_day_range(invalid_type)  # type: ignore[arg-type]


def test_validate_bbox():
    """Verify bbox validation normalizes valid input and rejects malformed or out-of-range bounds."""
    assert validate_bbox("100.0,5.5,101.0,6.5") == "100.0,5.5,101.0,6.5"
    assert validate_bbox([100.0, 5.5, 101.0, 6.5]) == "100.0,5.5,101.0,6.5"

    invalid_bboxes = [
        "101.0,5.5,100.0,6.5",  # west > east
        "100.0,5.5,100.0,6.5",  # west == east
        "100.0,6.5,101.0,5.5",  # south > north
        "100.0,5.5,101.0,5.5",  # south == north
        "-181.0,5.5,101.0,6.5",  # west < -180
        "100.0,5.5,181.0,6.5",  # east > 180
        "100.0,-91.0,101.0,6.5",  # south < -90
        "100.0,5.5,101.0,91.0",  # north > 90
        "100.0,5.5,101.0",  # only 3 coords
        "west,south,east,north",  # non-numeric
    ]
    for bad_bbox in invalid_bboxes:
        with pytest.raises(ValueError):
            validate_bbox(bad_bbox)

    with pytest.raises(TypeError):
        validate_bbox(12345)  # type: ignore[arg-type]


def test_client_env_key_and_optional_date(monkeypatch: pytest.MonkeyPatch):
    """Verify client map key resolution from environment, URL redaction, and area URL building with/without a date."""
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    with pytest.raises(ValueError, match="FIRMS_MAP_KEY"):
        FIRMSClient()

    monkeypatch.setenv("FIRMS_MAP_KEY", "env_secret_key")
    client = FIRMSClient(base_url="https://example.nasa.gov/api/")
    assert "env_secret_key" not in repr(client)

    url_no_date = client.build_area_url("MODIS_NRT", "100.0,5.5,101.0,6.5", day_range=3)
    assert (
        url_no_date
        == "https://example.nasa.gov/api/area/csv/env_secret_key/MODIS_NRT/100.0,5.5,101.0,6.5/3"
    )

    url_with_date = client.build_area_url(
        "MODIS_SP", [100.0, 5.5, 101.0, 6.5], day_range=5, date="2025-01-01"
    )
    assert (
        url_with_date
        == "https://example.nasa.gov/api/area/csv/env_secret_key/MODIS_SP/100.0,5.5,101.0,6.5/5/2025-01-01"
    )

    assert validate_query_date(date(2025, 1, 15)) == "2025-01-15"
    with pytest.raises(ValueError):
        validate_query_date("2025/01/15")
    with pytest.raises(ValueError):
        validate_query_date("2025-02-30")
    with pytest.raises(TypeError):
        validate_query_date(12345)  # type: ignore[arg-type]


def test_client_fetch_area_csv_and_http_200_error_body(monkeypatch: pytest.MonkeyPatch):
    """Verify fetch_area_csv returns CSV text on success and raises FIRMSAPIError on an HTTP 200 error body."""
    requested_urls: list[str] = []
    mock_body = f"{CSV_HEADER}\n{CSV_ROW_1}\n"

    async def mock_get(self, url: str, *args, **kwargs) -> httpx.Response:
        """Stub httpx GET that records the requested URL and returns a canned CSV response."""
        requested_urls.append(url)
        request = httpx.Request("GET", url)
        return httpx.Response(200, text=mock_body, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    client = FIRMSClient(map_key="unit_test_key")
    csv_text = asyncio.run(
        client.fetch_area_csv(
            "MODIS_SP", "100.0,5.5,101.0,6.5", day_range=5, date="2025-01-01"
        )
    )
    assert csv_text == mock_body
    assert requested_urls[-1].endswith("/MODIS_SP/100.0,5.5,101.0,6.5/5/2025-01-01")

    backend_client = BackendFIRMSClient(map_key="unit_test_key")
    resp = asyncio.run(
        backend_client.fetch_area("MODIS_NRT", "100.0,5.5,101.0,6.5", days=2)
    )
    assert isinstance(resp, httpx.Response)
    assert resp.status_code == 200

    mock_body = "Invalid MAP_KEY."
    with pytest.raises(FIRMSAPIError, match="Invalid MAP_KEY"):
        asyncio.run(client.fetch_area_csv("MODIS_NRT", "100.0,5.5,101.0,6.5", day_range=1))


def test_31_day_date_chunking():
    """Verify a 31-day range is chunked into six 5-day windows plus a final 1-day window."""
    chunks = chunk_date_range("2025-01-01", "2025-01-31")
    lengths = [days for _, days in chunks]
    assert lengths == [5, 5, 5, 5, 5, 5, 1]
    assert chunks == [
        ("2025-01-01", 5),
        ("2025-01-06", 5),
        ("2025-01-11", 5),
        ("2025-01-16", 5),
        ("2025-01-21", 5),
        ("2025-01-26", 5),
        ("2025-01-31", 1),
    ]

    with pytest.raises(ValueError):
        chunk_date_range("2025-01-10", "2025-01-01")


def test_downloader_dest_dir_creation_and_date_range_merge(tmp_path):
    """Verify the downloader creates nested destination directories and correctly merges chunked date-range downloads."""
    calls: list[tuple[str, str, int, str | None]] = []

    class StubFIRMSClient(FIRMSClient):
        """Stub FIRMS client that records calls and returns a single-row canned CSV."""

        def __init__(self):
            """Initialize the stub client with a fixed test map key."""
            super().__init__(map_key="stub_key")

        async def fetch_area_csv(
            self,
            source: str,
            bbox: str,
            day_range: int = 1,
            date: str | None = None,
        ) -> str:
            """Record the call arguments and return a canned single-row CSV response."""
            calls.append((source, str(bbox), day_range, date))
            row = f"5.1,100.2,312.4,1.0,1.0,{date or '2025-01-01'},0630,Terra,85,6.1,295.1,15.2,D"
            return f"{CSV_HEADER}\n{row}\n"

    dest_dir = tmp_path / "nested" / "raw" / "malaysia"
    assert not dest_dir.exists()

    downloader = FIRMSDownloader(client=StubFIRMSClient(), dest_dir=str(dest_dir))
    assert dest_dir.exists()

    single_path = asyncio.run(
        downloader.download_bbox("MODIS_NRT", "100.0,5.5,101.0,6.5", "single.csv")
    )
    assert (dest_dir / "single.csv").exists()
    assert single_path == str(dest_dir / "single.csv")

    calls.clear()
    range_path = asyncio.run(
        downloader.download_date_range(
            source="MODIS_SP",
            bbox="100.0,5.5,101.0,6.5",
            start_date="2025-01-01",
            end_date="2025-01-31",
            output_filename="malaysia_jan2025.csv",
            save_raw_chunks=True,
        )
    )
    assert len(calls) == 7
    assert [c[2] for c in calls] == [5, 5, 5, 5, 5, 5, 1]

    with open(range_path, "r", encoding="utf-8") as f:
        merged_text = f.read()

    lines = [line for line in merged_text.strip().splitlines() if line]
    # 1 header + 7 data rows (no duplicate headers)
    assert len(lines) == 8
    assert lines[0] == CSV_HEADER
    assert sum(1 for line in lines if line.startswith("latitude,")) == 1

    df = parse_firms_csv(merged_text)
    assert len(df) == 7
    assert downloader.last_download_metadata is not None
    assert downloader.last_download_metadata["chunk_lengths"] == [5, 5, 5, 5, 5, 5, 1]
    assert len(downloader.last_download_metadata["raw_chunk_paths"]) == 7


def test_combine_csv_chunks_handles_empty_chunks():
    """Verify combining CSV chunks skips empty and header-only chunks without duplicating headers."""
    c1 = f"{CSV_HEADER}\n{CSV_ROW_1}\n"
    c2 = f"{CSV_HEADER}\n"  # header-only chunk
    c3 = ""  # completely empty chunk
    c4 = f"{CSV_HEADER}\n{CSV_ROW_2}\n"

    combined = combine_csv_chunks([c1, c2, c3, c4])
    df = parse_firms_csv(combined)
    assert len(df) == 2


def test_region_lookup_and_global_configuration():
    """Verify known regions resolve to their configured bounding boxes, including global/world aliases."""
    regions = load_regions_config()
    assert "malaysia" in regions
    assert "indonesia" in regions
    assert "india" in regions
    assert "north_america" in regions
    assert "global" in regions
    assert "world" in regions

    assert resolve_region_bbox(region="malaysia") == ("malaysia", "100.0,5.5,101.0,6.5")
    assert resolve_region_bbox(region="indonesia") == ("indonesia", "101.0,-0.5,102.5,1.5")
    assert resolve_region_bbox(region="global") == ("global", "-180.0,-90.0,180.0,90.0")
    assert resolve_region_bbox(region="WORLD") == ("world", "-180.0,-90.0,180.0,90.0")
    assert resolve_region_bbox(region="custom_aoi", bbox=[10.0, 20.0, 30.0, 40.0]) == (
        "custom_aoi",
        "10.0,20.0,30.0,40.0",
    )
    assert resolve_region_bbox(bbox="10.0,20.0,30.0,40.0") == (
        "custom",
        "10.0,20.0,30.0,40.0",
    )


def test_invalid_region_and_malformed_regions_config(tmp_path):
    """Verify unknown regions, missing arguments, and malformed region config files raise appropriate errors."""
    with pytest.raises(ValueError, match="Unknown region"):
        resolve_region_bbox(region="atlantis")

    with pytest.raises(ValueError, match="Explicit 'region' or 'bbox'"):
        resolve_region_bbox()

    with pytest.raises(TypeError):
        resolve_region_bbox(region=123)  # type: ignore[arg-type]

    bad_yaml = tmp_path / "bad_regions.yaml"
    bad_yaml.write_text(
        "regions:\n  broken:\n    name: Broken\n    bbox: [120.0, 10.0, 100.0, 20.0]\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid bbox for region 'broken'"):
        load_regions_config(config_path=bad_yaml)


def test_cli_help_without_api_key(monkeypatch: pytest.MonkeyPatch, capsys):
    """Verify each ingestion CLI's --help output succeeds and lists expected options even without an API key."""
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    for parser_factory in (build_modis_parser, build_viirs_parser, build_all_parser):
        parser = parser_factory()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "--region" in captured.out
        assert "--start-date" in captured.out
        assert "--end-date" in captured.out
        assert "--mode" in captured.out
        assert "--output-dir" in captured.out


def test_ingestion_requires_explicit_arguments():
    """Verify ingestion functions raise ValueError when required region/bbox or date arguments are missing."""
    with pytest.raises(ValueError, match="Explicit 'region' or 'bbox'"):
        download_modis_data()
    with pytest.raises(ValueError, match="Explicit 'region' or 'bbox'"):
        download_viirs_data()
    with pytest.raises(ValueError, match="Explicit 'region' or 'bbox'"):
        download_all()
    with pytest.raises(ValueError, match="start_date"):
        download_modis_data(region="malaysia")


def test_ingestion_orchestration_sp_and_nrt_and_empty_results(tmp_path):
    """Verify orchestrated SP and NRT ingestion runs request the correct products and handle empty results."""
    calls: list[tuple[str, str, int, str | None]] = []
    return_empty = False

    class StubFIRMSClient(FIRMSClient):
        """Stub FIRMS client that can simulate either populated or empty responses."""

        def __init__(self):
            """Initialize the stub client with a fixed test map key."""
            super().__init__(map_key="stub_test_key")

        async def fetch_area_csv(
            self,
            source: str,
            bbox: str,
            day_range: int = 1,
            date: str | None = None,
        ) -> str:
            """Record the call arguments and return either a header-only or single-row canned CSV response."""
            calls.append((source, str(bbox), day_range, date))
            if return_empty:
                return f"{CSV_HEADER}\n"
            row = f"5.7,100.4,318.2,1.0,1.0,{date or '2025-01-01'},0545,Terra,88,6.1,296.0,14.5,D"
            return f"{CSV_HEADER}\n{row}\n"

    stub_client = StubFIRMSClient()

    # 1. Historical SP run for Malaysia Jan 2025 (MODIS_SP, VIIRS_SNPP_SP, VIIRS_NOAA20_SP)
    sp_results = download_all(
        region="malaysia",
        start_date="2025-01-01",
        end_date="2025-01-31",
        mode="sp",
        output_dir=tmp_path,
        client=stub_client,
    )
    assert [r["source"] for r in sp_results] == [
        MODIS_SP,
        VIIRS_SNPP_SP,
        VIIRS_NOAA20_SP,
    ]
    # 3 SP products * 7 five-day chunks = 21 requests
    assert len(calls) == 21
    for res in sp_results:
        assert res["region"] == "malaysia"
        assert res["bbox"] == "100.0,5.5,101.0,6.5"
        assert res["mode"] == "sp"
        assert res["row_count"] == 7
        assert res["is_empty"] is False
        assert res["chunk_lengths"] == [5, 5, 5, 5, 5, 5, 1]
        assert (tmp_path / "malaysia" / f"malaysia_{res['source']}_2025-01-01_2025-01-31.csv").is_file()

    # 2. Global NRT run across all 4 NRT products (including NOAA-21)
    calls.clear()
    nrt_results = download_all(
        region="global",
        start_date="2026-10-01",
        end_date="2026-10-03",
        mode="nrt",
        output_dir=tmp_path,
        client=stub_client,
    )
    assert [r["source"] for r in nrt_results] == [
        MODIS_NRT,
        VIIRS_SNPP_NRT,
        VIIRS_NOAA20_NRT,
        VIIRS_NOAA21_NRT,
    ]
    assert len(calls) == 4
    assert all(r["bbox"] == "-180.0,-90.0,180.0,90.0" for r in nrt_results)

    # 3. Empty result handling (header-only response)
    return_empty = True
    empty_results = download_modis_data(
        region="india",
        start_date="2025-01-01",
        end_date="2025-01-02",
        mode="sp",
        output_dir=tmp_path,
        client=stub_client,
    )
    assert len(empty_results) == 1
    assert empty_results[0]["row_count"] == 0
    assert empty_results[0]["is_empty"] is True


def test_settings_and_env_directory_resolution(monkeypatch: pytest.MonkeyPatch):
    """Verify data directory resolution from environment variables and that settings redact the FIRMS map key."""
    monkeypatch.setenv("DATA_RAW_DIR", "/tmp/stardust_raw")
    monkeypatch.setenv("DATA_INTERIM_DIR", "/tmp/stardust_interim")
    monkeypatch.setenv("DATA_PROCESSED_DIR", "/tmp/stardust_processed")
    dirs = get_pipeline_data_dirs()
    assert str(dirs["raw"]) == "/tmp/stardust_raw"
    assert str(dirs["interim"]) == "/tmp/stardust_interim"
    assert str(dirs["processed"]) == "/tmp/stardust_processed"

    cfg = Settings(
        FIRMS_MAP_KEY="top_secret_key",
        FIRMS_BASE_URL="https://custom.firms.nasa.gov/api",
    )
    assert "top_secret_key" not in repr(cfg)
    assert cfg.FIRMS_BASE_URL == "https://custom.firms.nasa.gov/api"
    assert cfg.DATA_RAW_DIR == "/tmp/stardust_raw"
