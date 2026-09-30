import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from irail_ingestion.exceptions import DateIsNotRightError

logger = logging.getLogger(__name__)


def build_storage_path(
    base_path: str, dataset: str, file_prefix: str, date_utc: datetime
) -> Path:
    """Construire le chemin d'un fichier à partir du dossier de base
    et de l'endpoint API"""
    if date_utc.tzinfo is None:
        raise DateIsNotRightError()

    date_utc_ready = date_utc.astimezone(UTC)
    path_to_build = Path(base_path) / dataset
    path_to_build = path_to_build / f"date={format_date(date_utc_ready)}"
    path_to_build = (
        path_to_build / f"{file_prefix}_{get_time_from_datetime(date_utc_ready)}.json"
    )

    return path_to_build


def write_payload_to_path(path_to_create: Path, payload: dict) -> Path:
    """Ecrire le payload à un chemin donne"""
    path_to_create.parent.mkdir(parents=True, exist_ok=True)
    path_to_create.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    logger.info("Path : %s, Size: %s", path_to_create, path_to_create.stat().st_size)

    return path_to_create


def format_date(date_to_format: datetime):
    return date_to_format.strftime("%Y-%m-%d")


def get_time_from_datetime(time_to_format: datetime):
    return time_to_format.strftime("%Y%m%dT%H%M%SZ")
