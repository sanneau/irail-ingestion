import logging

import pandas as pd
import psycopg

from irail_ingestion.config import DbSettings

logger = logging.getLogger(__name__)

CREATE_DIM_STATION_SQL = """CREATE TABLE IF NOT EXISTS dim_station (
    station_key      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    station_id       text NOT NULL UNIQUE,
    standard_name    text NOT NULL,
    longitude        double precision NOT NULL,
    latitude         double precision NOT NULL,
    snapshot_at      timestamptz NOT NULL,
    source_file      text NOT NULL);"""


UPSERT_DIM_STATION_SQL = """INSERT INTO dim_station (station_id, standard_name,
                         longitude, latitude, snapshot_at, source_file)
                          VALUES (%s, %s, %s, %s, %s, %s)
                          ON CONFLICT (station_id) DO UPDATE SET
                          standard_name = EXCLUDED.standard_name,
                          longitude = EXCLUDED.longitude,
                          latitude = EXCLUDED.latitude,
                          snapshot_at = EXCLUDED.snapshot_at,
                          source_file = EXCLUDED.source_file;"""


def station_rows(df: pd.DataFrame) -> list[tuple]:
    """Transforme un DataFrame de stations en une liste de tuples pour
    l'insertion SQL."""
    return list(
        df[
            [
                "station_id",
                "standard_name",
                "longitude",
                "latitude",
                "snapshot_at",
                "source_file",
            ]
        ].itertuples(index=False, name=None)
    )


def upsert_dim_station(db: DbSettings, rows: list[tuple]) -> int:
    """Insère ou met à jour les stations dans la table dim_station."""
    with psycopg.connect(
        host=db.host,
        port=db.port,
        dbname=db.name,
        user=db.user,
        password=db.password,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_DIM_STATION_SQL)
            cur.executemany(UPSERT_DIM_STATION_SQL, rows)
            return cur.rowcount
