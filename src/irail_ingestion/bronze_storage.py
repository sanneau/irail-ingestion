import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from irail_ingestion.exceptions import DateIsNotRightError, PayloadIsEmptyError

logger = logging.getLogger(__name__)


def build_storage_path(base_path: str, station_id: str, date_utc: datetime) -> Path:
    """Construire le chemin d'un fichier à partir du dossier de base,
    de la gare et de l'instant de l'appel"""
    if date_utc.tzinfo is None:
        raise DateIsNotRightError()

    date_utc_ready = date_utc.astimezone(UTC)
    path_to_build = Path(base_path) / "liveboard"

    path_to_build = path_to_build / f"date={format_date(date_utc_ready)}"
    path_to_build = (
        path_to_build / f"{station_id}_{get_time_from_datetime(date_utc_ready)}.json"
    )

    return path_to_build


def write_payload_to_path(path_to_create: Path, payload: dict, station_id: str) -> Path:
    """Ecrire le payload à un chemin donne"""
    if "departures" not in payload:
        raise PayloadIsEmptyError(
            f"Payload is empty for station {station_id}", station_id
        )

    path_to_create.parent.mkdir(parents=True, exist_ok=True)
    path_to_create.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    logger.info("Path : %s, Size: %s", path_to_create, path_to_create.stat().st_size)

    return path_to_create


def format_date(date_to_format: datetime):
    return date_to_format.strftime("%Y-%m-%d")


def get_time_from_datetime(time_to_format: datetime):
    return time_to_format.strftime("%Y%m%dT%H%M%SZ")
