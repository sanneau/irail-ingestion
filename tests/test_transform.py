from datetime import UTC, datetime

import pytest

from irail_ingestion.exceptions import ConvertionIsWrongError, InvalidSnapshotError
from irail_ingestion.transform import (
    from_payload_to_dataclass,
    from_txt_to_bool,
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
