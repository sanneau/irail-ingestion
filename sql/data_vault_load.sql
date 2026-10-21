-- Chargement insert-only du Data Vault depuis les stagings (stg_station, stg_departure).
-- Ordre : hubs -> link -> satellites (un link pointe vers des hubs, un satellite vers son hub ou son link).
-- Relançable : une 2e exécution sans changement n'insère rien.

INSERT INTO dv.hub_station (station_hk, station_id, load_date, record_source)
SELECT DISTINCT md5(upper(trim(station_id))), station_id, now(), 'irail'
FROM (
    SELECT station_id FROM stg_station
    UNION SELECT departure_station_id FROM stg_departure
    UNION SELECT destination_station_id FROM stg_departure
) AS toutes_les_gares
ON CONFLICT (station_hk) DO NOTHING;

INSERT INTO dv.hub_vehicle (vehicle_hk, vehicle_id, load_date, record_source)
SELECT DISTINCT md5(upper(trim(vehicle_id))), vehicle_id, now(), 'irail'
FROM stg_departure
ON CONFLICT (vehicle_hk) DO NOTHING;


INSERT INTO dv.link_departure (departure_hk, departure_station_hk,
destination_station_hk, vehicle_hk, scheduled_at, load_date, record_source)
SELECT DISTINCT
    md5(upper(trim(departure_station_id)) || '|' || upper(trim(destination_station_id)) || '|'
        || upper(trim(vehicle_id)) || '|' || (scheduled_at AT TIME ZONE 'UTC')::text),
    md5(upper(trim(departure_station_id))),
    md5(upper(trim(destination_station_id))),
    md5(upper(trim(vehicle_id))),
    scheduled_at, now(), 'irail'
FROM stg_departure
ON CONFLICT (departure_hk) DO NOTHING;


WITH derniere_version AS (
    SELECT DISTINCT ON (station_hk) station_hk, hash_diff
    FROM dv.sat_station
    ORDER BY station_hk, load_date DESC
),
nouvelles AS (
    SELECT md5(upper(trim(station_id))) AS station_hk,
           md5(coalesce(standard_name, '') || '|' || coalesce(longitude::text, '') || '|' || coalesce(latitude::text, '')) AS hash_diff,
           standard_name, longitude, latitude
    FROM stg_station
)
INSERT INTO dv.sat_station (station_hk, load_date, hash_diff, standard_name, longitude, latitude, record_source)
SELECT n.station_hk, now(), n.hash_diff, n.standard_name, n.longitude, n.latitude, 'irail'
FROM nouvelles AS n
LEFT JOIN derniere_version AS d ON d.station_hk = n.station_hk
WHERE d.hash_diff IS DISTINCT FROM n.hash_diff;


WITH derniere_version AS (
    SELECT DISTINCT ON (departure_hk) departure_hk, hash_diff
    FROM dv.sat_departure
    ORDER BY departure_hk, load_date DESC
),
nouvelles AS (
    SELECT md5(upper(trim(departure_station_id)) || '|' || upper(trim(destination_station_id)) || '|'
               || upper(trim(vehicle_id)) || '|' || (scheduled_at AT TIME ZONE 'UTC')::text) AS departure_hk,
           md5(coalesce(delay_s::text, '') || '|' || coalesce(canceled::text, '') || '|' || coalesce(is_extra::text, '')
            || '|' || coalesce(platform, '') || '|' || coalesce(platform_changed::text, '') || '|' || coalesce(occupancy, '')
            || '|' || coalesce(train_type, '') ) AS hash_diff,
            delay_s, canceled, is_extra, platform, platform_changed, occupancy, train_type
    FROM stg_departure
)
INSERT INTO dv.sat_departure (departure_hk, load_date, hash_diff, delay_s, canceled, is_extra, platform, platform_changed, occupancy, train_type, record_source)
SELECT n.departure_hk, now(), n.hash_diff, n.delay_s, n.canceled, n.is_extra, n.platform,
    n.platform_changed, n.occupancy, n.train_type,  'irail'
FROM nouvelles AS n
LEFT JOIN derniere_version AS d ON d.departure_hk = n.departure_hk
WHERE d.hash_diff IS DISTINCT FROM n.hash_diff;
