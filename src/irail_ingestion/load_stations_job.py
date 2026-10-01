import logging

import pandas as pd
import psycopg

from irail_ingestion.config import load_db_settings, load_settings
from irail_ingestion.logging_config import setup_logging
from irail_ingestion.warehouse import station_rows, upsert_dim_station

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None):
    setup_logging()
    db_settings = load_db_settings()
    user_settings = load_settings()
    dir_parquet_stations = user_settings.silver_dir / "stations/stations.parquet"
    station_data = pd.read_parquet(dir_parquet_stations)
    try:
        row_count = upsert_dim_station(db_settings, station_rows(station_data))
    except psycopg.OperationalError as e:
        logger.error("Erreur de connexion à la base de données : %s", e)
        row_count = 0
    if row_count == len(station_data):
        logger.info(
            "Succès : %d lignes insérées ou mises à jour dans dim_station.", row_count
        )
        return 0
    elif 1 <= row_count < len(station_data):
        logger.warning(
            "Attention : %d lignes insérées ou mises à jour dans dim_station"
            " sur %d lignes totales.",
            row_count,
            len(station_data),
        )
        return 1
    elif row_count == 0:
        logger.error("Erreur : aucune ligne insérée ou mise à jour dans dim_station.")
        return 1
