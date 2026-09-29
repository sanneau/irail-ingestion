import argparse
import json
import logging
import time
from datetime import UTC, datetime

from irail_ingestion.exceptions import InvalidSnapshotError
from irail_ingestion.logging_config import setup_logging
from irail_ingestion.silver_storage import read_files_in_b_date, write_silver_parquet
from irail_ingestion.transform import (
    build_dataframe_for_liveboard,
    from_file_name_to_snapshot,
    from_payload_to_dataclass,
    keep_latest_unique_row,
)

logger = logging.getLogger(__name__)

BASE_PATH_OF_SILVER_STORAGE = "data/silver/departures"
BASE_PATH_OF_BRONZE_PATH = "data/raw/liveboard"


def from_str_to_datetime(date_chosen: str) -> datetime:
    """Convert 'YYYY-MM-DD' into a datetime at midnight UTC."""
    return datetime.strptime(date_chosen, "%Y-%m-%d").replace(tzinfo=UTC)


def main(argv: list[str] | None = None) -> int:
    """Transform one day of bronze liveboard files into the silver Parquet."""
    start = time.monotonic()
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Transforme une journée de bronze en silver (Parquet)."
    )
    # type= : argparse appelle la fonction ; une date invalide → message clair + code 2
    parser.add_argument(
        "date", type=from_str_to_datetime, help="la journée à traiter (AAAA-MM-JJ, UTC)"
    )
    args = parser.parse_args(argv)
    date_final = args.date

    list_good_integration, list_bad_integration = [], []
    files_wrong = 0
    list_iteration = read_files_in_b_date(BASE_PATH_OF_BRONZE_PATH, date_final)
    for el in list_iteration:
        try:
            with el.open("r", encoding="utf-8") as f:
                list_to_integer, list_bad_integer = from_payload_to_dataclass(
                    json.load(f), from_file_name_to_snapshot(el.name), el.name
                )
        except (json.JSONDecodeError, ValueError, InvalidSnapshotError):
            logger.exception("wrong Files : %s", el)
            files_wrong += 1
        else:
            list_good_integration.extend(list_to_integer)
            list_bad_integration.extend(list_bad_integer)

    dataframe_not_finished = build_dataframe_for_liveboard(list_good_integration)
    dataframe_unique = keep_latest_unique_row(dataframe_not_finished)
    path_write = write_silver_parquet(
        dataframe_unique,
        BASE_PATH_OF_SILVER_STORAGE,
        date_final,
    )

    duration_s = time.monotonic() - start
    logger.info(
        "BILAN : ficher lue  -> %d, fichiers en erreur -> %d, départs -> %d,"
        " lignes rejetées -> %d, lignes après dédoublonnage -> %d, path -> %s,"
        " time total : %.1f s",
        len(list_iteration),
        files_wrong,
        len(list_good_integration),
        len(list_bad_integration),
        len(dataframe_unique),
        path_write,
        duration_s,
    )

    total_lines = len(list_bad_integration) + len(list_good_integration)
    if total_lines == 0:
        return 1  # aucune ligne : la collecte est probablement tombée → alerte
    if len(list_bad_integration) / total_lines * 100 > 30:
        return 1
    return 0
