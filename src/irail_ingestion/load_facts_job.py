import argparse
import logging

import pandas as pd
import psycopg

from irail_ingestion.config import load_db_settings, load_settings
from irail_ingestion.logging_config import setup_logging
from irail_ingestion.transform_job import from_str_to_datetime
from irail_ingestion.warehouse import departure_rows, upsert_fact_departures

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Orchestrateur pour l'ingestion de la table fact departures"""

    parser = argparse.ArgumentParser(
        description="Transforme une journée de silver (Parquet) vers "
        "entrepot de données."
    )
    parser.add_argument(
        "date", type=from_str_to_datetime, help="la journée à traiter (AAAA-MM-JJ, UTC)"
    )
    args = parser.parse_args(argv)
    date_final = args.date

    setup_logging()
    db_settings = load_db_settings()
    user_settings = load_settings()

    dir_parquet_fact_dep = user_settings.silver_dir / "departures"
    dir_suffix = "departures.parquet"
    dir_finale = dir_parquet_fact_dep / f"date={date_final:%Y-%m-%d}" / dir_suffix

    try:
        df_fact_dep = pd.read_parquet(dir_finale)
    except FileNotFoundError:
        logger.exception("file not found at the dates, directory : %s", dir_finale)
        return 1

    try:
        row_count = upsert_fact_departures(db_settings, departure_rows(df_fact_dep))
    except psycopg.OperationalError as e:
        logger.error("Erreur de connexion à la base de données : %s", e)
        row_count = 0
    if row_count == len(df_fact_dep):
        logger.info(
            "Succès : %d lignes insérées ou mises à jour dans fact_departures.",
            row_count,
        )
        return 0
    elif 1 <= row_count < len(df_fact_dep):
        logger.warning(
            "Attention : %d lignes insérées ou mises à jour"
            " dans fact_departures"
            " sur %d lignes totales.",
            row_count,
            len(df_fact_dep),
        )
        return 1
    elif row_count == 0:
        logger.error(
            "Erreur : aucune ligne insérée ou mise à jour dans fact_departures."
        )
        return 1
