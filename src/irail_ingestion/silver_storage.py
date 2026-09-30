import datetime as dt
import logging
from datetime import UTC
from pathlib import Path

import pandas as pd

from irail_ingestion.bronze_storage import format_date
from irail_ingestion.exceptions import DateIsNotRightError

logger = logging.getLogger(__name__)


def read_files_in_b_date(base_dir: Path, date_to_read: dt = "2026-09-28") -> list[Path]:
    """Give back the list of files for one date choose"""
    total_path = "date=" + format_date(date_to_read)
    base_path = Path(base_dir) / total_path
    return list(base_path.glob("**/*.json"))


def write_silver_parquet(
    df_of_liveboard: pd.DataFrame, silver_folder: Path, date_args: dt
) -> Path:
    """Construire le fichier parquet des liveboard"""

    if date_args.tzinfo is None:
        raise DateIsNotRightError()

    date_utc_ready = date_args.astimezone(UTC)
    path_to_build = Path(silver_folder)
    path_to_build = (
        path_to_build / f"date={format_date(date_utc_ready)}" / "departures.parquet"
    )
    path_to_build.parent.mkdir(parents=True, exist_ok=True)
    df_of_liveboard.to_parquet(
        path_to_build, engine="pyarrow", compression="snappy", index=False
    )
    return path_to_build


def write_stations_parquet_station(
    df_of_stations: pd.DataFrame, silver_dir: Path
) -> Path:
    """Construire le fichier parquet des station : ecrasé a chaque fois"""
    path_to_build = Path(silver_dir) / "stations" / "stations.parquet"
    path_to_build.parent.mkdir(parents=True, exist_ok=True)
    df_of_stations.to_parquet(
        path_to_build, engine="pyarrow", compression="snappy", index=False
    )
    return path_to_build
