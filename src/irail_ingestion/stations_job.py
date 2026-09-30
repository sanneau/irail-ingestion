import argparse
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from irail_ingestion.bronze_storage import build_storage_path, write_payload_to_path
from irail_ingestion.client import build_session, fetch_stations
from irail_ingestion.config import Settings, load_settings
from irail_ingestion.exceptions import InvalidSnapshotError, IRailAPIError
from irail_ingestion.logging_config import setup_logging
from irail_ingestion.silver_storage import write_stations_parquet_station
from irail_ingestion.transform import (
    build_dataframe_for_station,
    from_file_name_to_snapshot,
    from_payload_to_dataclass_station,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Collect the iRail station list into bronze, then rebuild the silver table."""
    argparse.ArgumentParser(
        description="Collecte la liste des gares iRail (bronze) "
        "et reconstruit la dimension gares (silver)."
    ).parse_args(argv)

    start = time.monotonic()
    setup_logging()
    user_settings = load_settings()
    session_request = build_session(user_settings)

    try:
        fetched_at = datetime.now(tz=UTC)
        payload = fetch_stations(session_request, user_settings)
    except IRailAPIError:
        logger.exception("Stations retrieval failed")
        return 1

    bronze_path = write_payload_to_path(
        build_storage_path(user_settings.data_dir, "stations", "stations", fetched_at),
        payload,
    )
    written = station_silver_part(user_settings, bronze_path)

    logger.info("BILAN stations : durée totale %.1f s", time.monotonic() - start)
    return 0 if written > 0 else 1


def station_silver_part(user_settings: Settings, bronze_path: Path) -> int:
    """Rebuild the silver station table from one bronze file.

    Returns the number of stations written (0 if the bronze file is unusable).
    """
    try:
        with bronze_path.open("r", encoding="utf-8") as f:
            stations, rejects = from_payload_to_dataclass_station(
                json.load(f),
                from_file_name_to_snapshot(bronze_path.name),
                bronze_path.name,
            )
    except (json.JSONDecodeError, ValueError, InvalidSnapshotError):
        logger.exception("Unusable bronze file: %s", bronze_path)
        return 0

    silver_path = write_stations_parquet_station(
        build_dataframe_for_station(stations), user_settings.silver_dir
    )
    logger.info(
        "Gares écrites : %d, rejetées : %d, parquet : %s",
        len(stations),
        len(rejects),
        silver_path,
    )
    return len(stations)
