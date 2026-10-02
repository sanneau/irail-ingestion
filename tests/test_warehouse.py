from datetime import UTC, datetime

from irail_ingestion.transform import (
    build_dataframe_for_station,
    from_payload_to_dataclass_station,
)
from irail_ingestion.warehouse import station_rows

SOURCE_FILE = "stations_20260930T071856Z.json"
SNAPSHOT_AT = datetime(2026, 9, 30, 7, 18, 56, tzinfo=UTC)


def test_station_rows_follow_the_insert_column_order(payload_station):
    stations, _ = from_payload_to_dataclass_station(
        payload_station, SNAPSHOT_AT, SOURCE_FILE
    )
    rows = station_rows(build_dataframe_for_station(stations))

    assert len(rows) == 3
    assert all(len(row) == 6 for row in rows)
    station_id, name, longitude, latitude, snapshot_at, source_file = rows[0]
    assert (station_id, name) == ("BE.NMBS.008863446", "Sclaigneaux")
    assert (longitude, latitude) == (5.026363, 50.492247)  # X = longitude
    assert isinstance(longitude, float) and isinstance(latitude, float)
    assert (snapshot_at, source_file) == (SNAPSHOT_AT, SOURCE_FILE)
