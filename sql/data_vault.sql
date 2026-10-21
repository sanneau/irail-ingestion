CREATE SCHEMA IF NOT EXISTS dv;

CREATE TABLE IF NOT EXISTS dv.hub_station (
    station_hk    char(32)    NOT NULL PRIMARY KEY,
    station_id    text        NOT NULL UNIQUE,
    load_date     timestamptz NOT NULL,
    record_source text        NOT NULL
);

CREATE TABLE IF NOT EXISTS dv.hub_vehicle (
    vehicle_hk  char(32)    NOT NULL PRIMARY KEY,
    vehicle_id  text        NOT NULL UNIQUE,
    load_date     timestamptz NOT NULL,
    record_source text        NOT NULL
);

CREATE TABLE IF NOT EXISTS dv.link_departure (
    departure_hk    char(32) NOT NULL PRIMARY KEY,
    departure_station_hk    char(32)  NOT NULL REFERENCES dv.hub_station,
    destination_station_hk  char(32) NOT NULL  REFERENCES dv.hub_station,
    vehicle_hk  char(32) NOT NULL REFERENCES dv.hub_vehicle,
    scheduled_at    timestamptz NOT NULL,
    load_date   timestamptz NOT NULL,
    record_source   text        NOT NULL
);

CREATE TABLE IF NOT EXISTS dv.sat_station (
    station_hk char(32) NOT NULL REFERENCES dv.hub_station,
    load_date timestamptz NOT NULL,
    hash_diff char(32) NOT NULL,
    standard_name text NOT NULL,
    longitude float,
    latitude float,
    record_source text NOT NULL,
    PRIMARY KEY (station_hk, load_date)
);

CREATE TABLE IF NOT EXISTS dv.sat_departure (
    departure_hk     char(32)    NOT NULL REFERENCES dv.link_departure,
    load_date        timestamptz NOT NULL,
    hash_diff        char(32)    NOT NULL,
    delay_s          integer     NOT NULL,
    canceled         boolean     NOT NULL,
    is_extra         boolean     NOT NULL,
    platform         text,
    platform_changed boolean     NOT NULL,
    occupancy        text,
    train_type       text        NOT NULL,
    record_source    text        NOT NULL,
    PRIMARY KEY (departure_hk, load_date)
);

-- Étoile par-dessus le Data Vault : dim_station SCD 2 recalculée depuis le hub et le satellite.
DROP VIEW IF EXISTS dv.v_dim_station;
CREATE VIEW dv.v_dim_station AS
WITH versions AS (
    SELECT h.station_id, s.standard_name, s.longitude, s.latitude, s.load_date,
           LAG(s.load_date)  OVER (PARTITION BY s.station_hk ORDER BY s.load_date) AS load_date_precedente,
           LEAD(s.load_date) OVER (PARTITION BY s.station_hk ORDER BY s.load_date) AS load_date_suivante
    FROM dv.hub_station AS h
    INNER JOIN dv.sat_station AS s ON h.station_hk = s.station_hk
)
SELECT station_id, standard_name, longitude, latitude,
       CASE WHEN load_date_precedente IS NULL THEN '1900-01-01'::timestamptz ELSE load_date END AS valid_from,
       coalesce(load_date_suivante, '9999-12-31') AS valid_to,
       load_date_suivante IS NULL AS is_current
FROM versions;
