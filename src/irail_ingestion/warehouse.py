import logging

import pandas as pd
import psycopg

from irail_ingestion.config import DbSettings

logger = logging.getLogger(__name__)

CREATE_DIM_STATION_SQL = """
    CREATE TABLE IF NOT EXISTS dim_station (
    station_key      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    station_id       text NOT NULL UNIQUE,
    standard_name    text NOT NULL,
    longitude        double precision NULL,
    latitude         double precision NULL,
    snapshot_at      timestamptz NOT NULL,
    source_file      text NOT NULL);"""


CREATE_DIM_DATE_SQL = """
    CREATE TABLE IF NOT EXISTS dim_date (
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

CREATE_DIM_TIME_SQL = """
    CREATE TABLE IF NOT EXISTS dim_time (
    time_key      integer PRIMARY KEY,
    full_time     text NOT NULL,
    hour          integer NOT NULL,
    minute        integer NOT NULL,
    time_band     text NOT NULL,
    is_peak       boolean NOT NULL);"""

CREATE_FACT_DEPARTURE_SQL = """
    CREATE TABLE IF NOT EXISTS fact_departure (
    departure_key bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    departure_station_key   integer NOT NULL,
    destination_station_key   integer NOT NULL,
    date_key    integer NOT NULL,
    time_key    integer NOT NULL,
    platform    text,
    delay_s     integer NOT NULL,
    canceled    boolean NOT NULL,
    is_extra    boolean NOT NULL,
    train_type      text NOT NULL,
    occupancy   text NULL,
    vehicle_id  text NOT NULL,
    scheduled_at     timestamp with time zone NOT NULL,
    platform_changed    boolean NOT NULL,
    snapshot_at     timestamp with time zone NOT NULL,
    source_file     text NOT NULL,
    FOREIGN KEY (departure_station_key) REFERENCES dim_station (station_key),
    FOREIGN KEY (destination_station_key) REFERENCES dim_station (station_key),
    FOREIGN KEY (date_key) REFERENCES dim_date (date_key),
    FOREIGN KEY (time_key) REFERENCES dim_time (time_key),
    UNIQUE (departure_station_key, scheduled_at, vehicle_id));"""

TRUNCATE_STG_DEPARTURES = """ TRUNCATE stg_departure; """

CREATE_STG_DEPARTURE_SQL = """
    CREATE TABLE IF NOT EXISTS stg_departure(
    departure_station_id   text,
    departure_station_name   text,
    snapshot_at      timestamp with time zone,
    scheduled_at    timestamp with time zone,
    delay_s        integer,
    canceled       boolean,
    is_extra       boolean,
    destination_station_id   text,
    destination_station_name   text,
    vehicle_id      text,
    train_type      text,
    occupancy       text,
    platform_changed       boolean,
    platform        text,
    source_file     text
    ); """

UPSERT_DIM_DATE_SQL = """
    INSERT INTO dim_date (date_key, full_date, year,
    quarter , month, month_name, iso_week, day_of_month,
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

UPSERT_DIM_STATION_SQL = """
    INSERT INTO dim_station (station_id, standard_name,
    longitude, latitude, snapshot_at, source_file)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (station_id) DO UPDATE SET
    standard_name = EXCLUDED.standard_name,
    longitude = EXCLUDED.longitude,
    latitude = EXCLUDED.latitude,
    snapshot_at = EXCLUDED.snapshot_at,
    source_file = EXCLUDED.source_file;"""


UPSERT_DIM_TIME_SQL = """
    INSERT INTO dim_time (time_key, full_time, hour,
    minute, time_band, is_peak)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (time_key) DO UPDATE SET
    full_time = EXCLUDED.full_time,
    hour = EXCLUDED.hour,
    minute = EXCLUDED.minute,
    time_band = EXCLUDED.time_band,
    is_peak = EXCLUDED.is_peak;"""


INSERT_STG_DEPARTURES_SQL = """
    INSERT INTO stg_departure (departure_station_id,
    departure_station_name, snapshot_at, scheduled_at,
    delay_s, canceled, is_extra, destination_station_id,
    destination_station_name, vehicle_id, train_type,
    occupancy, platform_changed, platform, source_file)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s);"""


UPSERT_FACT_DEPARTURES = """
    INSERT INTO fact_departure (departure_station_key,
    destination_station_key, date_key, time_key,
    scheduled_at, vehicle_id, delay_s, canceled, is_extra,
    platform_changed, train_type, platform, occupancy,
    snapshot_at, source_file) SELECT
    coalesce(dep.station_key, -1),
    coalesce(dest.station_key, -1),
    to_char(s.scheduled_at AT TIME ZONE
    'Europe/Brussels', 'YYYYMMDD')::int,
    to_char(s.scheduled_at AT TIME ZONE
    'Europe/Brussels', 'HH24MI')::int,
    s.scheduled_at, s.vehicle_id, s.delay_s, s.canceled,
    s.is_extra, s.platform_changed,
    s.train_type, s.platform, s.occupancy, s.snapshot_at, s.source_file
    FROM stg_departure AS s
    LEFT JOIN dim_station AS dep
    ON dep.station_id  = s.departure_station_id
    LEFT JOIN dim_station AS dest
    ON dest.station_id = s.destination_station_id
    ON CONFLICT (departure_station_key, scheduled_at, vehicle_id)
    DO UPDATE SET
    delay_s = EXCLUDED.delay_s,
    canceled = EXCLUDED.canceled,
    is_extra = EXCLUDED.is_extra,
    platform_changed = EXCLUDED.platform_changed,
    train_type = EXCLUDED.train_type,
    platform = EXCLUDED.platform,
    occupancy = EXCLUDED.occupancy,
    snapshot_at = EXCLUDED.snapshot_at,
    source_file = EXCLUDED.source_file;"""


STATION_KEY_UNKNOWS = """
    INSERT INTO dim_station (station_key, station_id,
    standard_name, longitude, latitude, snapshot_at, source_file)
    OVERRIDING SYSTEM VALUE
    VALUES (-1, 'UNKNOWNS', 'Gare inconnue', NULL, NULL,
    '1970-01-01', 'membre inconnu')
    ON CONFLICT (station_id) DO NOTHING;"""


UNKNOWN_STATIONS_SQL = """
    SELECT s.departure_station_id
    FROM stg_departure AS s
    LEFT JOIN dim_station AS d ON d.station_id = s.departure_station_id
    WHERE d.station_key IS NULL
    UNION
    SELECT s.destination_station_id
    FROM stg_departure AS s
    LEFT JOIN dim_station AS d ON d.station_id = s.destination_station_id
    WHERE d.station_key IS NULL
    ORDER BY 1;"""


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


def departure_rows(df: pd.DataFrame) -> list[tuple]:
    """Transforme un DataFrame de départs en une liste de tuples pour
    l'insertion SQL. Les valeurs manquantes (pd.NA) deviennent None (NULL)."""
    columns = df[
        [
            "departure_station_id",
            "departure_station_name",
            "snapshot_at",
            "scheduled_at",
            "delay_s",
            "canceled",
            "is_extra",
            "destination_station_id",
            "destination_station_name",
            "vehicle_id",
            "train_type",
            "occupancy",
            "platform_changed",
            "platform",
            "source_file",
        ]
    ]
    return list(
        columns.astype(object)
        .where(columns.notna(), None)
        .itertuples(index=False, name=None)
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


def upsert_fact_departures(db: DbSettings, rows: list[tuple]) -> int:
    """Insère ou met à jour les départs dans la table fact_departures."""
    with psycopg.connect(
        host=db.host,
        port=db.port,
        dbname=db.name,
        user=db.user,
        password=db.password,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_STG_DEPARTURE_SQL)
            cur.execute(TRUNCATE_STG_DEPARTURES)
            cur.executemany(INSERT_STG_DEPARTURES_SQL, rows)
            cur.execute(UNKNOWN_STATIONS_SQL)
            unknown_stations = [row[0] for row in cur.fetchall()]
            cur.execute(CREATE_FACT_DEPARTURE_SQL)
            cur.execute(UPSERT_FACT_DEPARTURES)
            loaded = cur.rowcount
            if unknown_stations:
                logger.warning(
                    "%d gare(s) absente(s) de dim_station, départs rattachés au "
                    "membre inconnu (-1) : %s. Relancer irail-stations, "
                    "puis recharger ce jour.",
                    len(unknown_stations),
                    ", ".join(unknown_stations),
                )
            return loaded
