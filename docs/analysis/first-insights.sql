-- Toutes les partitions silver en une seule "table" logique.
-- Les requêtes suivantes lisent `departures` au lieu de répéter le chemin.
CREATE OR REPLACE VIEW departures AS SELECT * FROM "data/silver/departures/*/*.parquet";

-- 1. Pour chaque gare : le nombre de départs, et le nombre en retard (≥ 6 min, soit delay_s >= 360, et non annulés).
SELECT departure_station_name AS "STATION_DEPART",
    count(*) AS "NOMBRE DE DEPART",
    count(*) FILTER (WHERE delay_s  >= 360) AS "NOMBRE DE TRAINS EN RETARD",
FROM departures
GROUP BY (departure_station_id, departure_station_name)
ORDER BY  count(*) desc;

-- 2. Quel est le retard moyen et le retard maximal de chaque gare ? Quelles gares arrivent en tête ?
SELECT departure_station_name AS "STATION_DEPART",
    ROUND(AVG(delay_s/60), 1) AS "AVERAGE RETARD (MINUTES)",
    MAX(delay_s/60) AS "MAXIMUM RETARD (MINUTES)"
FROM departures
GROUP BY (departure_station_id, departure_station_name)
ORDER BY MAX(delay_s) desc;

--3. quel est le taux de ponctualité (en %) de chaque type de train (IC, S, L, P, BUS…) ?
SELECT train_type AS "TYPE DE TRAIN",
    count(*) AS "NOMBRE DE DEPART",
    count(*) FILTER (WHERE delay_s < 360) AS "NOMBRE DE TRAINS PONCTUELS",
    round((count(*) FILTER (WHERE delay_s  < 360)/count(*)) * 100, 1) AS "ponctualité_pct"
FROM departures
GROUP BY (train_type)
ORDER BY (count(*) FILTER (WHERE delay_s  < 360)/count(*)) * 100 desc;

--4. Requête 4 : la ponctualité par heure de la journée (heure belge)
SELECT hour(timezone('Europe/Brussels', scheduled_at)) AS "HEURE",
    count(*) AS "NOMBRE DE DEPART",
    round((count(*) FILTER (WHERE delay_s  < 360)/count(*)) * 100, 1) AS "ponctualité_pct"
FROM departures
GROUP BY hour(timezone('Europe/Brussels', scheduled_at))
ORDER BY hour(timezone('Europe/Brussels', scheduled_at)) ASC;

--5. les données respectent-elles le contrat de docs/silver-schema.md ?
SELECT  count(*) AS "lignes",
    count(DISTINCT (departure_station_id, vehicle_id, scheduled_at)) AS "cles_distinctes",
    count(*) FILTER (WHERE departure_station_id IS NULL) AS "null_station",
    count(*) FILTER (WHERE vehicle_id IS NULL) AS "null_vehicle",
    count(*) FILTER (WHERE scheduled_at IS NULL) AS "null_scheduled",
    count(*) FILTER (WHERE delay_s IS NULL) AS "null_delay"
FROM departures;
