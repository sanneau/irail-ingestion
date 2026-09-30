from datetime import UTC, datetime

import pytest

from irail_ingestion.exceptions import ConvertionIsWrongError, InvalidSnapshotError
from irail_ingestion.transform import (
    from_file_name_to_snapshot,
    from_payload_to_dataclass,
    from_payload_to_dataclass_station,
    from_txt_to_bool,
    from_txt_to_float,
    from_txt_to_int,
    replace_sentinel_value,
)

# Un vrai nom de fichier bronze, et l'instant qui correspond à son horodatage
SOURCE_FILE = "BE.NMBS.008813003_20260924T135000Z.json"
SNAPSHOT_AT = datetime(2026, 9, 24, 13, 50, 0, tzinfo=UTC)


class TestTransform:
    @pytest.mark.parametrize("test_input,expected", [("0", False), ("1", True)])
    def test_from_txt_to_bool(self, test_input, expected):
        assert from_txt_to_bool(test_input) == expected

    @pytest.mark.parametrize("test_input", ["abs", "3"])
    def test_from_txt_to_bool_exception(self, test_input):
        with pytest.raises(ConvertionIsWrongError):
            assert from_txt_to_bool(test_input)

    @pytest.mark.parametrize("test_input,expected", [("1", 1), ("1000", 1000)])
    def test_from_txt_to_int(self, test_input, expected):
        assert from_txt_to_int(test_input) == expected

    @pytest.mark.parametrize("test_input", ["abs", "sdfsdfgsdfg"])
    def test_from_txt_to_int_exception(self, test_input):
        with pytest.raises(ConvertionIsWrongError):
            assert from_txt_to_int(test_input)

    @pytest.mark.parametrize(
        "test , sentinelle, result",
        [
            (9, 9, None),
            ("abracadrabra", "abracadrabra", None),
            ("abracadrabra", "abracadra", "abracadrabra"),
        ],
    )
    def test_replace_sentinel_value(self, test, sentinelle, result):
        assert replace_sentinel_value(test, sentinelle) == result

    def test_valid_from_payload_to_dataclass(self, payload):
        departures, rejects = from_payload_to_dataclass(
            payload, SNAPSHOT_AT, SOURCE_FILE
        )

        assert rejects == []
        assert len(departures) == 1
        dep = departures[0]
        assert dep.departure_station_id == "BE.NMBS.008813003"
        assert dep.destination_station_id == "BE.NMBS.008833001"
        assert dep.vehicle_id == "BE.NMBS.S23765"
        # les règles de conversion du contrat silver
        assert dep.scheduled_at == datetime(2026, 9, 24, 14, 4, tzinfo=UTC)
        assert dep.delay_s == 0
        assert dep.canceled is False
        assert dep.platform_changed is False
        assert dep.snapshot_at == SNAPSHOT_AT
        assert dep.source_file == SOURCE_FILE

    def test_from_payload_to_dataclass_station(self, payload_station):
        stations, rejects = from_payload_to_dataclass_station(
            payload_station, SNAPSHOT_AT, SOURCE_FILE
        )
        assert rejects == []
        assert len(stations) == 3
        sta = stations[0]
        assert sta.station_id == "BE.NMBS.008863446"
        assert sta.standard_name == "Sclaigneaux"
        assert sta.api_generated_at == datetime(2026, 9, 30, 7, 18, 56, tzinfo=UTC)
        assert isinstance(sta.longitude, float)
        assert sta.longitude == 5.026363  # locationX = longitude
        assert sta.latitude == 50.492247  # locationY = latitude
        assert sta.snapshot_at == SNAPSHOT_AT
        assert sta.source_file == SOURCE_FILE

    def test_invalid_coordinate_rejects_only_that_station(self, payload_station):
        payload_station["station"][1]["locationX"] = "abc"
        stations, rejects = from_payload_to_dataclass_station(
            payload_station, SNAPSHOT_AT, SOURCE_FILE
        )
        assert len(stations) == 2
        assert len(rejects) == 1
        assert rejects[0]["raw"]["id"] == "BE.NMBS.008843133"
        assert "abc" in rejects[0]["reason"]

    @pytest.mark.parametrize("payload_change", ["delete_key", "empty_list"])
    def test_station_payload_without_stations_is_invalid(
        self, payload_station, payload_change
    ):
        if payload_change == "delete_key":
            del payload_station["station"]
        else:
            payload_station["station"] = []
        with pytest.raises(InvalidSnapshotError):
            from_payload_to_dataclass_station(payload_station, SNAPSHOT_AT, SOURCE_FILE)

    @pytest.mark.parametrize(
        "text, expected", [("50.84", 50.84), ("-1.672744", -1.672744), ("4", 4.0)]
    )
    def test_from_txt_to_float(self, text, expected):
        assert from_txt_to_float(text) == expected

    @pytest.mark.parametrize("text", ["abc", "", None, "nan", "inf"])
    def test_from_txt_to_float_rejects_invalid(self, text):
        with pytest.raises(ConvertionIsWrongError):
            from_txt_to_float(text)

    def test_invalid_no_departures(self, payload):
        # Arrange
        del payload["departures"]
        # Assess
        with pytest.raises(InvalidSnapshotError):
            # Act
            from_payload_to_dataclass(payload, SNAPSHOT_AT, SOURCE_FILE)

    def test_invalid_empty_departures(self, payload):
        # Arrange
        payload["departures"] = []
        # Assess
        with pytest.raises(InvalidSnapshotError):
            # Act
            from_payload_to_dataclass(payload, SNAPSHOT_AT, SOURCE_FILE)

    def test_zero_departures_is_not_an_error(self, payload):
        payload["departures"] = {"number": "0", "departure": []}
        assert from_payload_to_dataclass(payload, SNAPSHOT_AT, SOURCE_FILE) == ([], [])

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (
                "/home/sanneau/projects/irail-ingestion/data/raw/liveboard/date=2026-09-25/BE.NMBS.008813003_20260925T172320Z.json",
                datetime(2026, 9, 25, 17, 23, 20, tzinfo=UTC),
            ),
            (
                "data/raw/liveboard/date=2026-09-29/BE.NMBS.008813003_20260929T114844Z.json",
                datetime(2026, 9, 29, 11, 48, 44, tzinfo=UTC),
            ),
        ],
    )
    def test_from_file_name_to_snapshot_valid_date(self, test_input, expected):
        assert from_file_name_to_snapshot(test_input) == expected

    @pytest.mark.parametrize(
        "test_input",
        [
            ("pas-une-date.json"),
            ("84851855"),
            ("BE.NMBS.008813003_20261340T000000Z.json"),
        ],
    )
    def test_from_file_name_to_snapshot_not_a_date(self, test_input):
        with pytest.raises(ConvertionIsWrongError):
            from_file_name_to_snapshot(test_input)
