import argparse
import logging
from datetime import UTC, date
from datetime import datetime as dt
from pathlib import Path

import pandas as pd
import psycopg

from irail_ingestion.config import load_db_settings, load_settings
from irail_ingestion.logging_config import setup_logging
from irail_ingestion.warehouse import (
    departure_rows,
    loaded_days,
    log_load_failure,
    upsert_fact_departures,
)

logger = logging.getLogger(__name__)


def missing_days(available: set[date], loaded: set[date]) -> list[date]:
    """Calcul la liste des jour présent dans la silver mais pas dans la
    table etl_load_log et la trie en ascending"""
    return sorted(list(available.difference(loaded)))


def available_days(silver_dir: Path) -> set[date]:
    list_cleaned = set()
    list_files = sorted(silver_dir.glob("date=*"))
    for el in list_files:
        list_cleaned.add(date.fromisoformat(el.name.removeprefix("date=")))
    return list_cleaned


def main(argv: list[str] | None = None) -> int:
    """Orchestrateur pour l'ingestion de la table fact departures"""
    setup_logging()

    parser = argparse.ArgumentParser(
        prog="load_facts_job", description="Ingest silver departure to Data Warehouse"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("date", nargs="?", type=date.fromisoformat)
    group.add_argument("--missing", action="store_true")
    args = parser.parse_args(argv)

    db_settings = load_db_settings()
    user_settings = load_settings()

    if args.missing:
        days = missing_days(
            available_days(user_settings.silver_dir / "departures"),
            loaded_days(db_settings),
        )
        if not days:
            logger.info("Nothing to load")
            return 0
    else:
        days = [args.date]

    failures = 0
    for day in days:
        if load_one_day(day) != 0:
            failures += 1
    if failures >= 1:
        return 1
    else:
        return 0


def load_one_day(date_run: date) -> int:
    db_settings = load_db_settings()
    user_settings = load_settings()
    started_at = dt.now(UTC)

    dir_parquet_fact_dep = user_settings.silver_dir / "departures"
    dir_suffix = "departures.parquet"
    dir_finale = dir_parquet_fact_dep / f"date={date_run:%Y-%m-%d}" / dir_suffix

    try:
        df_fact_dep = pd.read_parquet(dir_finale)
    except FileNotFoundError:
        logger.exception("file not found at the dates, directory : %s", dir_finale)
        return 1

    try:
        row_count = upsert_fact_departures(
            db_settings, departure_rows(df_fact_dep), date_run, started_at
        )
    except psycopg.Error as e:
        logger.error("Erreur de connexion à la base de données : %s", e)
        try:
            log_load_failure(db_settings, date_run, started_at, str(e))
        except psycopg.Error:
            logger.error("Impossible d'écrire l'échec dans etl_load_log")
        return 1
    logger.info("Success : We have had a new dates rows : %s", row_count)
    return 0
