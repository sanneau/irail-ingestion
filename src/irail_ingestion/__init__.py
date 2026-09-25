import logging
import time
from datetime import UTC, datetime

from irail_ingestion.client import build_session, fetch_liveboard
from irail_ingestion.config import load_settings
from irail_ingestion.exceptions import IRailAPIError
from irail_ingestion.logging_config import setup_logging
from irail_ingestion.storage import build_storage_path, write_payload_to_path

PAUSE_BETWEEN_STATIONS_S = 0.5

logger = logging.getLogger(__name__)


def main() -> int:
    start = time.monotonic()
    count_error = count_succeed = 0
    setup_logging()
    user_settings = load_settings()
    session_request = build_session(user_settings)
    for station in user_settings.station_ids:
        try:
            fetched_at = datetime.now(tz=UTC)
            payload_to_write = fetch_liveboard(session_request, user_settings, station)
        except IRailAPIError:
            count_error += 1
            logger.exception("station %s did not work", station)
        else:
            count_succeed += 1
            write_payload_to_path(
                build_storage_path(user_settings.data_dir, station, fetched_at),
                payload_to_write,
                station,
            )

        time.sleep(PAUSE_BETWEEN_STATIONS_S)

    duration_s = time.monotonic() - start
    logger.info(
        "station succeed : %s, station failed : %s, time total : %.1f s",
        count_succeed,
        count_error,
        duration_s,
    )
    if count_error == 0:
        return 0
    else:
        return 1
