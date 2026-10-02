import logging

import pandas as pd
import psycopg

from irail_ingestion.config import DbSettings

logger = logging.getLogger(__name__)

CREATE_DIM_STATION_SQL = """CREATE TABLE IF NOT EXISTS dim_station (
    station_key      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    station_id       text NOT NULL UNIQUE,
    standard_name    text NOT NULL,
    longitude        double precision NULL,
    latitude         double precision NULL,
    snapshot_at      timestamptz NOT NULL,
    source_file      text NOT NULL);"""


CREATE_DIM_DATE_SQL = """CREATE TABLE IF NOT EXISTS dim_date (
    date_key      integer PRIMARY KEY,
    full_date     date NOT NULL,
    year          integer NOT NULL,
    quarter       integer NOT NULL,
    month         integer NOT NULL,
    month_name    text NOT NULL,
    iso_week      integer NOT NULL,
    day_of_month  integer NOT NULL,
    day_of_week   integer NOT NULL,
    day_name      text NOT NULL,
    is_weekend    boolean NOT NULL,
    is_holiday    boolean NOT NULL,
    holiday_name  text );"""

CREATE_DIM_TIME_SQL = """CREATE TABLE IF NOT EXISTS dim_time (
    time_key      integer PRIMARY KEY,
    full_time     text NOT NULL,
    hour          integer NOT NULL,
    minute        integer NOT NULL,
    time_band     text NOT NULL,
    is_peak       boolean NOT NULL);"""


UPSERT_DIM_DATE_SQL = """INSERT INTO dim_date (date_key, full_date, year, quarter
                        , month, month_name, iso_week, day_of_month,
                        day_of_week, day_name,
                        is_weekend, is_holiday, holiday_name)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (date_key) DO UPDATE SET
                        full_date = EXCLUDED.full_date,
                        year = EXCLUDED.year,
                        quarter = EXCLUDED.quarter,
                        month = EXCLUDED.month,
                        month_name = EXCLUDED.month_name,
                        iso_week = EXCLUDED.iso_week,
                        day_of_month = EXCLUDED.day_of_month,
                        day_of_week = EXCLUDED.day_of_week,
                        day_name = EXCLUDED.day_name,
                        is_weekend = EXCLUDED.is_weekend,
                        is_holiday = EXCLUDED.is_holiday,
                        holiday_name = EXCLUDED.holiday_name;"""

UPSERT_DIM_STATION_SQL = """INSERT INTO dim_station (station_id, standard_name,
                         longitude, latitude, snapshot_at, source_file)
                          VALUES (%s, %s, %s, %s, %s, %s)
                          ON CONFLICT (station_id) DO UPDATE SET
                          standard_name = EXCLUDED.standard_name,
                          longitude = EXCLUDED.longitude,
                          latitude = EXCLUDED.latitude,
                          snapshot_at = EXCLUDED.snapshot_at,
                          source_file = EXCLUDED.source_file;"""


UPSERT_DIM_TIME_SQL = """INSERT INTO dim_time (time_key, full_time, hour,
                         minute, time_band, is_peak)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (time_key) DO UPDATE SET
                        full_time = EXCLUDED.full_time,
                        hour = EXCLUDED.hour,
                        minute = EXCLUDED.minute,
                        time_band = EXCLUDED.time_band,
                        is_peak = EXCLUDED.is_peak;"""

STATION_KEY_UNKNOWS = """ INSERT INTO dim_station (station_key, station_id,
                        standard_name, longitude, latitude, snapshot_at, source_file)
                        OVERRIDING SYSTEM VALUE
                        VALUES (-1, 'UNKNOWNS', 'Gare inconnue', NULL, NULL,
                        '1970-01-01', 'membre inconnu')
                        ON CONFLICT (station_id) DO NOTHING;"""


def date_rows_to_tuples(rows: list) -> list[tuple]:
    """Convertit une liste de DateRow en une liste de tuples
    pour l'insertion SQL."""
    return [
        (
            row.date_key,
            row.full_date,
            row.year,
            row.quarter,
            row.month,
            row.month_name,
            row.iso_week,
            row.day_of_month,
            row.day_of_week,
            row.day_name,
            row.is_weekend,
            row.is_holiday,
            row.holiday_name,
        )
        for row in rows
    ]


def time_rows_to_tuples(rows: list) -> list[tuple]:
    """Convertit une liste de TimeRow en une liste de tuples pour l'insertion SQL."""
    return [
        (
            row.time_key,
            row.full_time,
            row.hour,
            row.minute,
            row.time_band,
            row.is_peak,
        )
        for row in rows
    ]


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


def upsert_dim_date(db: DbSettings, rows: list[tuple]) -> int:
    """Insère ou met à jour les dates dans la table dim_date."""
    with psycopg.connect(
        host=db.host,
        port=db.port,
        dbname=db.name,
        user=db.user,
        password=db.password,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_DIM_DATE_SQL)
            cur.executemany(UPSERT_DIM_DATE_SQL, rows)
            return cur.rowcount


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
            cur.execute(STATION_KEY_UNKNOWS)
            cur.executemany(UPSERT_DIM_STATION_SQL, rows)
            return cur.rowcount


def upsert_dim_time(db: DbSettings, rows: list[tuple]) -> int:
    """Insère ou met à jour les heures dans la table dim_time."""
    with psycopg.connect(
        host=db.host,
        port=db.port,
        dbname=db.name,
        user=db.user,
        password=db.password,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_DIM_TIME_SQL)
            cur.executemany(UPSERT_DIM_TIME_SQL, rows)
            return cur.rowcount
