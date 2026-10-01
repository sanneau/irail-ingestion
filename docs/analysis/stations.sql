-- Jointures entre la table de faits silver (departures) et la dimension gares (stations).
-- Lancement : uv run python formation/run_sql.py docs/analysis/stations.sql
CREATE OR REPLACE VIEW departures AS SELECT * FROM 'data/silver/departures/*/*.parquet';
CREATE OR REPLACE VIEW stations AS SELECT * FROM 'data/silver/stations/stations.parquet';

-- 1. Les 10 destinations les plus fréquentes, avec le nom officiel et les coordonnées
--    issus de la DIMENSION (et non des départs).
--    LEFT JOIN : un départ dont la destination manquerait dans stations resterait visible
--    (colonnes de gare à NULL) au lieu de disparaître en silence comme avec un INNER JOIN.
SELECT
    d.destination_station_id,
    s.standard_name AS destination,
    s.latitude,
    s.longitude,
    count(*) AS departs
FROM departures AS d
LEFT JOIN stations AS s ON s.station_id = d.destination_station_id
GROUP BY ALL
ORDER BY departs DESC
LIMIT 10;

-- 2. Intégrité référentielle (anti-jointure) : des départs dont la destination
--    n'existe pas dans la dimension ?
--    Observé le 01/10 : 0 ligne (65 destinations distinctes, toutes présentes).
SELECT
    d.destination_station_id,
    any_value(d.destination_station_name) AS nom_dans_les_departs,
    count(*) AS departs
FROM departures AS d
LEFT JOIN stations AS s ON s.station_id = d.destination_station_id
WHERE s.station_id IS NULL
GROUP BY ALL;

-- 3. Retard moyen par gare de DÉPART (la jointure se fait sur departure_station_id :
--    la même dimension, jouée dans un autre rôle), avec l'effectif et les coordonnées.
SELECT
    s.standard_name AS gare_de_depart,
    s.latitude,
    s.longitude,
    count(*) AS departs,
    round(avg(d.delay_s) / 60, 1) AS retard_moyen_min
FROM departures AS d
LEFT JOIN stations AS s ON s.station_id = d.departure_station_id
GROUP BY ALL
ORDER BY retard_moyen_min DESC;

-- 4. Contrôle de la dimension : une seule ligne par gare ? (sinon : fan-out des jointures)
SELECT count(*) AS lignes, count(DISTINCT station_id) AS gares_distinctes FROM stations;
