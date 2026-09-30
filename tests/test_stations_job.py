from pathlib import Path

import pandas as pd
import pytest
import responses
from tenacity import wait_none

from irail_ingestion.client import fetch_stations
from irail_ingestion.stations_job import main

BASE_URL = "https://api.irail.be/v1"
STATIONS_URL = f"{BASE_URL}/stations"


@pytest.fixture
def stations_env(tmp_path, monkeypatch) -> Path:
    """Configuration pointing bronze and silver to tmp_path (no .env needed)."""
    monkeypatch.setenv("IRAIL_BASE_URL", BASE_URL)
    monkeypatch.setenv("IRAIL_USER_AGENT", "irail-test")
    monkeypatch.setenv("IRAIL_STATION_IDS", "BE.NMBS.008813003")
    monkeypatch.setenv("IRAIL_DATA_DIR", str(tmp_path / "raw"))
    monkeypatch.setenv("IRAIL_SILVER_DIR", str(tmp_path / "silver"))
    return tmp_path


@responses.activate
def test_job_writes_bronze_and_silver(stations_env, payload_station):
    responses.add(responses.GET, STATIONS_URL, json=payload_station, status=200)

    exit_code = main([])

    bronze_files = list((stations_env / "raw" / "stations").glob("date=*/*.json"))
    silver = pd.read_parquet(stations_env / "silver" / "stations" / "stations.parquet")
    assert exit_code == 0
    assert len(bronze_files) == 1
    assert bronze_files[0].name.startswith("stations_")
    assert len(silver) == 3
    assert set(silver["station_id"]) == {s["id"] for s in payload_station["station"]}
    assert (silver["source_file"] == bronze_files[0].name).all()


@responses.activate
def test_api_down_returns_1_and_writes_nothing(stations_env, monkeypatch):
    responses.add(responses.GET, STATIONS_URL, status=500)
    # The job calls fetch_stations with its real backoff (several seconds):
    # replace it WHERE IT IS USED (in stations_job) by a copy without waiting.
    monkeypatch.setattr(
        "irail_ingestion.stations_job.fetch_stations",
        fetch_stations.retry_with(wait=wait_none()),
    )

    exit_code = main([])

    assert exit_code == 1
    assert not (stations_env / "raw" / "stations").exists()
    assert not (stations_env / "silver").exists()
