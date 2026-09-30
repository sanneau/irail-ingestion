from datetime import UTC
from datetime import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from irail_ingestion.bronze_storage import build_storage_path
from irail_ingestion.exceptions import DateIsNotRightError

BASE_PATH = "data/raw"


@pytest.mark.parametrize(
    "base_path, station_id, date_utc ,expected",
    [
        (
            BASE_PATH,
            "BE.NMBS.008813003",
            dt(2026, 9, 25, 17, 59, 12, tzinfo=UTC),
            "data/raw/liveboard/date=2026-09-25/BE.NMBS.008813003_20260925T175912Z.json",
        ),
        (
            BASE_PATH,
            "BE.NMBS.008841400",
            dt(2026, 9, 25, 18, 59, 12, tzinfo=UTC),
            "data/raw/liveboard/date=2026-09-25/BE.NMBS.008841400_20260925T185912Z.json",
        ),
        (
            BASE_PATH,
            "BE.NMBS.008841400",
            dt(2026, 9, 26, 1, 30, 00, tzinfo=ZoneInfo("Europe/Brussels")),
            "data/raw/liveboard/date=2026-09-25/BE.NMBS.008841400_20260925T233000Z.json",
        ),
    ],
)
def test_build_storage_path_valid(base_path, station_id, date_utc, expected):
    """Testing if the valid is doing is job correctly"""
    assert build_storage_path(base_path, station_id, date_utc) == Path(expected)


@pytest.mark.parametrize(
    "base_path, station_id, date_utc",
    [(BASE_PATH, "BE.NMBS.008813003", dt(2026, 9, 25, 17, 59, 12, tzinfo=None))],
)
def test_build_storage_path_date_utc_invalid(base_path, station_id, date_utc):
    """Testing if TzInfo is right"""
    with pytest.raises(DateIsNotRightError):
        build_storage_path(base_path, station_id, date_utc)  # Act
