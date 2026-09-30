import logging
import math
from datetime import UTC, datetime

import pandas as pd

from irail_ingestion.exceptions import ConvertionIsWrongError, InvalidSnapshotError
from irail_ingestion.models import Departure, Station

logger = logging.getLogger(__name__)

SILVER_SCHEMA_LIVEBOARD: dict[str, str] = {
    "departure_station_id": "string",
    "departure_station_name": "string",
    "snapshot_at": "datetime64[ns, UTC]",
    "scheduled_at": "datetime64[ns, UTC]",
    "delay_s": "Int64",
    "canceled": "boolean",
    "is_extra": "boolean",
    "destination_station_id": "string",
    "destination_station_name": "string",
    "vehicle_id": "string",
    "train_type": "string",
    "platform": "string",
    "platform_changed": "boolean",
    "occupancy": "string",
    "source_file": "string",
}

SILVER_SCHEMA_STATION: dict[str, str] = {
    "station_id": "string",
    "standard_name": "string",
    "longitude": "Float64",
    "latitude": "Float64",
    "api_generated_at": "datetime64[ns, UTC]",
    "snapshot_at": "datetime64[ns, UTC]",
    "source_file": "string",
}

PRIMARY_KEY = ["departure_station_id", "scheduled_at", "vehicle_id"]


def from_txt_to_int(text: str) -> int:
    try:
        return int(text)
    except (ValueError, TypeError) as e:
        raise ConvertionIsWrongError(f"Entier invalide : {text!r}") from e


def from_txt_to_float(text: str) -> float:
    try:
        value = float(text)
    except (ValueError, TypeError) as e:
        raise ConvertionIsWrongError(f"Nombre décimal invalide : {text!r}") from e
    # float() accepte "nan", "NaN", "inf", "-Infinity", "1e999"… : on vérifie la VALEUR
    if not math.isfinite(value):
        raise ConvertionIsWrongError(f"Nombre non fini (NaN ou infini) : {text!r}")
    return value


def from_txt_to_bool(txtbool: str) -> bool:
    try:
        if txtbool == "0":
            return False
        elif txtbool == "1":
            return True
        else:
            raise ValueError
    except ValueError as e:
        raise ConvertionIsWrongError(f"Entier invalide : {txtbool!r}") from e


def replace_sentinel_value(txt_not_right: str, sentinel: str) -> str | None:
    if txt_not_right == sentinel:
        return None
    return txt_not_right


def from_txt_to_time(time: str) -> datetime:
    from_txt_to_int(time)
    return datetime.fromtimestamp(from_txt_to_int(time), tz=UTC)


def from_file_name_to_snapshot(file_name: str) -> datetime:
    try:
        timestamp_part = file_name.removesuffix(".json").rsplit("_", 1)[-1]
        date_valid = datetime.strptime(timestamp_part, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=UTC
        )
        return date_valid
    except ValueError as e:
        raise ConvertionIsWrongError(f"File Name Invalid : {file_name!r}") from e


def from_payload_to_dataclass(
    payload: dict, snapshot_at: datetime, source_file: str
) -> tuple[list[Departure], list[dict]]:
    list_good_item, list_wrong_item = [], []
    if payload.get("departures"):
        for raw in payload["departures"]["departure"]:
            try:
                list_good_item.append(
                    Departure(
                        departure_station_id=payload["stationinfo"]["id"],
                        departure_station_name=payload["stationinfo"]["standardname"],
                        snapshot_at=snapshot_at,
                        scheduled_at=from_txt_to_time(raw["time"]),
                        delay_s=from_txt_to_int(raw["delay"]),
                        canceled=from_txt_to_bool(raw["canceled"]),
                        is_extra=from_txt_to_bool(raw["isExtra"]),
                        destination_station_id=raw["stationinfo"]["id"],
                        destination_station_name=raw["stationinfo"]["standardname"],
                        vehicle_id=raw["vehicle"],
                        train_type=raw["vehicleinfo"]["type"],
                        platform=replace_sentinel_value(raw["platform"], "?"),
                        platform_changed=not from_txt_to_bool(
                            raw["platforminfo"]["normal"]
                        ),
                        occupancy=replace_sentinel_value(
                            raw["occupancy"]["name"], "unknown"
                        ),
                        source_file=source_file,
                    )
                )
            except (ValueError, TypeError, KeyError) as e:
                logger.warning("Ligne rejetée dans %s : %s", source_file, e)
                list_wrong_item.append(
                    {"source_file": source_file, "reason": str(e), "raw": raw}
                )
    else:
        raise InvalidSnapshotError()
    return (list_good_item, list_wrong_item)


def from_payload_to_dataclass_station(
    payload: dict, snapshot_at: datetime, source_file: str
) -> tuple[list[Station], list[dict]]:
    list_good_item, list_wrong_item = [], []
    if payload.get("station"):
        for raw in payload["station"]:
            try:
                list_good_item.append(
                    Station(
                        standard_name=raw["standardname"],
                        station_id=raw["id"],
                        latitude=from_txt_to_float(raw["locationY"]),
                        longitude=from_txt_to_float(raw["locationX"]),
                        snapshot_at=snapshot_at,
                        api_generated_at=from_txt_to_time(payload["timestamp"]),
                        source_file=source_file,
                    )
                )
            except (ValueError, TypeError, KeyError) as e:
                logger.warning("Ligne rejetée dans %s : %s", source_file, e)
                list_wrong_item.append(
                    {"source_file": source_file, "reason": str(e), "raw": raw}
                )
    else:
        raise InvalidSnapshotError()
    return (list_good_item, list_wrong_item)


def build_dataframe_for_liveboard(raw_checked: list[Departure]) -> pd.DataFrame:
    df = pd.DataFrame(raw_checked, columns=list(SILVER_SCHEMA_LIVEBOARD.keys()))
    return df.astype(SILVER_SCHEMA_LIVEBOARD)


def build_dataframe_for_station(raw_checked: list[Station]) -> pd.DataFrame:
    df = pd.DataFrame(raw_checked, columns=list(SILVER_SCHEMA_STATION.keys()))
    return df.astype(SILVER_SCHEMA_STATION)


def keep_latest_unique_row(data_table: pd.DataFrame) -> pd.DataFrame:
    dataframe_sorted = data_table.sort_values(
        by=["departure_station_id", "scheduled_at", "vehicle_id", "snapshot_at"],
        ascending=False,
    )
    return dataframe_sorted.drop_duplicates(
        subset=PRIMARY_KEY, keep="first", ignore_index=True
    )
