import json
from pathlib import Path

import pytest
import requests

from irail_ingestion.client import build_session
from irail_ingestion.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Une configuration de test : aucune variable d'environnement nécessaire."""
    return Settings(
        base_url="https://api.irail.be/v1",
        user_agent="irail-test",
        station_ids=("BE.NMBS.008813003",),
        data_dir=Path("unused"),
        silver_dir=Path("unused"),
        timeout_s=1.0,
    )


@pytest.fixture
def b_session(settings) -> requests.Session:
    """créer un build session a passer en parametre"""
    return build_session(settings)


@pytest.fixture
def bronze_env(tmp_path, monkeypatch, payload) -> Path:
    """Configure l'environnement vers tmp_path et
    y dépose un fichier bronze du 24/09."""
    monkeypatch.setenv("IRAIL_BASE_URL", "https://api.irail.be/v1")
    monkeypatch.setenv("IRAIL_USER_AGENT", "test")
    monkeypatch.setenv("IRAIL_STATION_IDS", "BE.NMBS.008813003")
    monkeypatch.setenv("IRAIL_DATA_DIR", str(tmp_path / "raw"))
    monkeypatch.setenv("IRAIL_SILVER_DIR", str(tmp_path / "silver"))

    bronze_day = tmp_path / "raw" / "liveboard" / "date=2026-09-24"
    bronze_day.mkdir(parents=True)
    bronze_file = bronze_day / "BE.NMBS.008813003_20260924T135000Z.json"
    bronze_file.write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path


@pytest.fixture
def payload_station() -> dict:
    """Un payload /stations iRail valide, avec 3 gares (dont une étrangère)."""
    return {
        "version": "1.4",
        "timestamp": "1790752736",
        "station": [
            {
                "@id": "http://irail.be/stations/NMBS/008863446",
                "id": "BE.NMBS.008863446",
                "name": "Sclaigneaux",
                "locationX": "5.026363",
                "locationY": "50.492247",
                "standardname": "Sclaigneaux",
            },
            {
                "@id": "http://irail.be/stations/NMBS/008843133",
                "id": "BE.NMBS.008843133",
                "name": "Sclessin",
                "locationX": "5.558911",
                "locationY": "50.609844",
                "standardname": "Sclessin",
            },
            {
                "@id": "http://irail.be/stations/NMBS/008721405",
                "id": "BE.NMBS.008721405",
                "name": "Selestat",
                "locationX": "7.449999",
                "locationY": "48.26667",
                "standardname": "Selestat",
            },
        ],
    }


@pytest.fixture
def payload() -> dict:
    """Un payload liveboard iRail valide, avec un seul départ."""
    return {
        "version": "1.4",
        "timestamp": "1790258846",
        "station": "Bruxelles-Central",
        "stationinfo": {
            "@id": "http://irail.be/stations/NMBS/008813003",
            "id": "BE.NMBS.008813003",
            "name": "Bruxelles-Central",
            "locationX": "4.356801",
            "locationY": "50.845658",
            "standardname": "Brussel-Centraal/Bruxelles-Central",
        },
        "departures": {
            "number": "1",
            "departure": [
                {
                    "id": "0",
                    "station": "Louvain",
                    "stationinfo": {
                        "@id": "http://irail.be/stations/NMBS/008833001",
                        "id": "BE.NMBS.008833001",
                        "name": "Louvain",
                        "locationX": "4.715866",
                        "locationY": "50.88228",
                        "standardname": "Leuven",
                    },
                    "time": "1790258640",
                    "delay": "0",
                    "canceled": "0",
                    "left": "0",
                    "isExtra": "0",
                    "vehicle": "BE.NMBS.S23765",
                    "vehicleinfo": {
                        "name": "BE.NMBS.S23765",
                        "shortname": "S2 3765",
                        "number": "3765",
                        "type": "S2",
                        "locationX": "0",
                        "locationY": "0",
                        "@id": "http://irail.be/vehicle/S23765",
                    },
                    "platform": "3",
                    "platforminfo": {"name": "3", "normal": "1"},
                    "occupancy": {
                        "@id": "http://api.irail.be/terms/low",
                        "name": "low",
                    },
                    "departureConnection": "http://irail.be/connections/8813003/20260924/S23765",
                }
            ],
        },
    }
