import logging
from datetime import date

import psycopg

from irail_ingestion.calendar_dim import build_date_rows, build_time_rows
from irail_ingestion.config import load_db_settings
from irail_ingestion.logging_config import setup_logging
from irail_ingestion.warehouse import (
    date_rows_to_tuples,
    time_rows_to_tuples,
    upsert_dim_date,
    upsert_dim_time,
)

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    """
    Main function to run the script to load date rows into the dim_date table.
    """
    setup_logging()
    db_settings = load_db_settings()
    start_date = date(2024, 1, 1)
    end_date = date(2030, 12, 31)
    # Build date, time rows and convert them to tuples for insertion
    date_rows = build_date_rows(start_date, end_date)
    time_rows = build_time_rows()

    date_tuples = date_rows_to_tuples(date_rows)
    time_tuples = time_rows_to_tuples(time_rows)

    try:
        upsert_dim_date(db_settings, date_tuples)
        upsert_dim_time(db_settings, time_tuples)
    except psycopg.OperationalError as e:
        logger.error("Database connection error: %s", e)
        return 0
    if len(date_rows) == len(date_tuples):
        logger.info(
            "Successfully inserted or updated %d rows in dim_date.", len(date_rows)
        )
        return 0
    elif 1 <= len(date_rows) < len(date_tuples):
        logger.warning(
            "Warning: %d rows inserted or updated in dim_date out of %d total rows.",
            len(date_rows),
            len(date_tuples),
        )
        return 1
    elif len(date_rows) == 0:
        logger.error("Error: No rows inserted or updated in dim_date.")
        return 1
