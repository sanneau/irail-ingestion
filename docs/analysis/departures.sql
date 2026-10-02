--E1
SELECT
    t.time_band,
    count(*)                                                   AS departs,
    round(avg(f.delay_s) / 60.0, 1)                            AS retard_moyen_min,
    round(100.0 * count(*) FILTER (WHERE f.delay_s < 360 AND NOT f.canceled)
          / count(*), 1)                                       AS ponctualite_pct,
    round(100.0 * count(*) / sum(count(*)) OVER (), 1)         AS part_du_trafic_pct,
    rank() OVER (ORDER BY avg(f.delay_s) DESC)                 AS rang_retard
FROM fact_departure AS f
JOIN dim_time AS t ON t.time_key = f.time_key
GROUP BY t.time_band
ORDER BY min(t.time_key);


--E2
SELECT
	day_name,
	round(100.0 * count(*) FILTER (WHERE f.delay_s < 360 AND NOT f.canceled) / count(*), 1) AS ponctualite_pct
FROM fact_departure AS f
JOIN dim_date AS t ON t.date_key = f.date_key
GROUP BY day_name, day_of_week
ORDER BY day_of_week;

--E3
WITH classement AS (
	SELECT
		t.hour as tranche_horaire,
		s.standard_name AS name_dep,
		COUNT (*) AS number_dep,
		ROUND(AVG(delay_s)) AS average_delay_s,
		row_number() OVER (PARTITION BY t.hour ORDER BY avg(delay_s) DESC) AS RANK_time
	FROM fact_departure AS f
	JOIN dim_time AS t ON t.time_key = f.time_key
	JOIN dim_station AS s ON s.station_key = f.destination_station_key
	GROUP BY t.hour, f.destination_station_key, s.standard_name
	HAVING COUNT(*) >= 10
	ORDER BY t.hour
	)
SELECT
		tranche_horaire,
		name_dep,
		number_dep,
		average_delay_s,
		RANK_time
	FROM classement
	WHERE RANK_time <= 3
	ORDER BY tranche_horaire, rank_time ASC
