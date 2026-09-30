from datetime import UTC, datetime

import pandas as pd

from irail_ingestion.silver_storage import write_stations_parquet_station
from irail_ingestion.transform import (
    SILVER_SCHEMA_STATION,
    build_dataframe_for_station,
    from_payload_to_dataclass_station,
)

SOURCE_FILE = "stations_20260930T071856Z.json"
SNAPSHOT_AT = datetime(2026, 9, 30, 7, 18, 56, tzinfo=UTC)


def _stations(payload_station):
    stations, _ = from_payload_to_dataclass_station(
        payload_station, SNAPSHOT_AT, SOURCE_FILE
    )
    return stations


def test_dataframe_has_the_contract_types(payload_station):
    df = build_dataframe_for_station(_stations(payload_station))

    assert len(df) == 3
    assert list(df.columns) == list(SILVER_SCHEMA_STATION)
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    assert dtypes == SILVER_SCHEMA_STATION


def test_empty_list_gives_typed_empty_dataframe():
    df = build_dataframe_for_station([])

    assert len(df) == 0
    assert list(df.columns) == list(SILVER_SCHEMA_STATION)
    assert str(df["latitude"].dtype) == "Float64"


def test_writing_twice_keeps_one_file_with_same_content(tmp_path, payload_station):
    df = build_dataframe_for_station(_stations(payload_station))

    first_path = write_stations_parquet_station(df, tmp_path)
    first = pd.read_parquet(first_path)
    second_path = write_stations_parquet_station(df, tmp_path)
    second = pd.read_parquet(second_path)

    assert first_path == second_path == tmp_path / "stations" / "stations.parquet"
    assert len(list(first_path.parent.iterdir())) == 1
    pd.testing.assert_frame_equal(first, second)


def test_parquet_round_trip_keeps_types(tmp_path, payload_station):
    df = build_dataframe_for_station(_stations(payload_station))

    reread = pd.read_parquet(write_stations_parquet_station(df, tmp_path))

    pd.testing.assert_frame_equal(reread, df)
