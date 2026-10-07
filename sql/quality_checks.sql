--C1
SELECT departure_station_key, scheduled_at, vehicle_id  FROM fact_departure
GROUP BY departure_station_key, scheduled_at, vehicle_id
HAVING count(*) > 1;

--C2
SELECT s.station_key
FROM fact_departure AS d
LEFT JOIN dim_station AS s ON d.departure_station_key = s.station_key
WHERE s.station_key = -1
UNION
SELECT j.station_key
FROM fact_departure as p
LEFT JOIN dim_station AS j ON p.destination_station_key = j.station_key
WHERE j.station_key = -1;

--C3
SELECT *
FROM fact_departure AS d
LEFT JOIN dim_date AS s ON d.date_key = s.date_key
WHERE s.year IS null;

--C4
SELECT departure_key, scheduled_at, date_key, time_key
FROM fact_departure
WHERE date_key IS DISTINCT FROM
        to_char(scheduled_at AT TIME ZONE 'Europe/Brussels', 'YYYYMMDD')::int
   OR time_key IS DISTINCT FROM
        to_char(scheduled_at AT TIME ZONE 'Europe/Brussels', 'HH24MI')::int;

--C5
SELECT *
FROM fact_departure
WHERE delay_s < 0;

--C6
SELECT scheduled_at, vehicle_id, array_agg(departure_station_key) AS station_keys
FROM fact_departure
GROUP BY scheduled_at, vehicle_id
HAVING bool_or(departure_station_key = -1)
   AND bool_or(departure_station_key <> -1);

--C7
SELECT station_id FROM dim_station GROUP BY station_id HAVING count(*) FILTER (WHERE is_current) > 1;

--C8
WITH VERSIONS AS (SELECT station_id, valid_from, valid_to, LEAD(valid_from) OVER (PARTITION BY station_id ORDER BY valid_from) AS next_valid_from  FROM dim_station)
SELECT * FROM VERSIONS WHERE valid_to IS DISTINCT FROM coalesce(next_valid_from, '9999-12-31');

--C9
SELECT station_id, valid_from, valid_to FROM dim_station WHERE valid_from >= valid_to;

--C10
SELECT station_id, f.scheduled_at, f.vehicle_id
FROM dim_station as s
JOIN fact_departure AS f ON s.station_key = f.departure_station_key
GROUP BY  station_id, f.scheduled_at, f.vehicle_id
HAVING count(*) > 1;
