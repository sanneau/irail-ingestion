# Modèle en étoile — ponctualité SNCB

> Modèle dimensionnel (Kimball) de l'entrepôt PostgreSQL, construit à partir de la couche silver.
> Statut : conçu le 01/10/2026 ; `dim_station` est chargée, `fact_departure` et `dim_date` sont l'objet du jour 8.

## Grain

**`fact_departure` : 1 ligne = 1 départ d'un train depuis une gare, à une heure prévue** (la dernière photo connue de ce départ).

## Diagramme

```mermaid
erDiagram
    fact_departure }o--|| dim_station : "departure_station_key (gare de départ)"
    fact_departure }o--|| dim_station : "destination_station_key (gare de destination)"
    fact_departure }o--|| dim_date : "date_key (jour du départ prévu)"
    fact_departure }o--|| dim_time : "time_key (heure du départ prévu)"

    fact_departure {
        bigint departure_key PK "clé de substitution technique"
        int departure_station_key FK "→ dim_station (rôle : départ)"
        int destination_station_key FK "→ dim_station (rôle : destination)"
        int date_key FK "→ dim_date, date de Bruxelles de scheduled_at"
        int time_key FK "→ dim_time, heure de Bruxelles de scheduled_at"
        timestamptz scheduled_at UK "heure prévue (fait partie du grain)"
        text vehicle_id UK "dimension dégénérée (fait partie du grain)"
        int delay_s "mesure : dernier retard annoncé (s)"
        boolean canceled "mesure : 0/1, se compte"
        boolean is_extra "mesure : 0/1, se compte"
        boolean platform_changed "mesure : 0/1, se compte"
        text train_type "attribut dégénéré (pas de dimension pour l'instant)"
        text platform "attribut dégénéré, nullable"
        text occupancy "attribut dégénéré, nullable"
        timestamptz snapshot_at "technique : quand le départ a été observé"
        text source_file "technique : lignage vers le bronze"
    }

    dim_station {
        int station_key PK "clé de substitution (IDENTITY)"
        text station_id UK "clé naturelle iRail"
        text standard_name "nom officiel"
        float8 longitude
        float8 latitude
        timestamptz snapshot_at "technique"
        text source_file "technique"
    }

    dim_date {
        int date_key PK "AAAAMMJJ, ex. 20261001"
        date full_date UK
        smallint year
        smallint quarter
        smallint month
        text month_name
        smallint iso_week
        smallint day_of_month
        smallint day_of_week "1 = lundi … 7 = dimanche (ISO)"
        text day_name
        boolean is_weekend
        boolean is_holiday "jour férié belge"
        text holiday_name "nullable"
    }

    dim_time {
        int time_key PK "HHMM, ex. 830 = 08 h 30 (1 ligne par minute)"
        smallint hour
        smallint minute
        text time_band "night, morning_peak, morning, noon, afternoon, evening_peak, evening"
        boolean is_peak
    }
```

Lecture des liens : `}o--||` = **plusieurs** départs (zéro ou plus) pour **exactement une** gare / une date (relation N:1, typique entre une table de faits et une dimension).

## Décisions

1. **Le grain** est garanti par la contrainte **`UNIQUE (departure_station_key, scheduled_at, vehicle_id)`** : la même clé naturelle qu'en silver, exprimée avec la clé de substitution de la gare. `departure_key` est une clé primaire technique (convention Kimball) ; l'unicité métier vient du `UNIQUE`.
2. **Les clés étrangères sont des clés de substitution** (`…_station_key`, `date_key`), retrouvées **au chargement** par un *lookup* sur la clé naturelle (`station_id`). Les faits ne référencent jamais directement les identifiants iRail.
3. **`dim_station` joue deux rôles** (dimension à rôles multiples) : une seule table, deux clés étrangères, deux jointures avec des alias.
4. **La date d'un départ vient de `scheduled_at`** (le jour où le train part), pas de `snapshot_at` (le jour où nous l'avons observé), **calculée dans le fuseau de Bruxelles** : on stocke l'instant en UTC, on dérive la date métier dans le fuseau du métier (`to_char(scheduled_at AT TIME ZONE 'Europe/Brussels', 'YYYYMMDD')::int`). Mesuré : 30 départs sur 2 843 changent de jour entre UTC et Bruxelles.
5. **`vehicle_id` est une dimension dégénérée pour l'instant** : il reste dans la table de faits et fait partie du grain, faute d'attributs à décrire aujourd'hui. **Évolution prévue** : quand les endpoints `vehicle` / `composition` d'iRail seront ingérés (relation de l'itinéraire, type de matériel…), on créera une `dim_vehicle` et la table de faits portera une `vehicle_key` (clé de substitution, retrouvée par lookup sur `vehicle_id`), comme pour les gares.
6. **`train_type`, `platform`, `occupancy` restent des attributs de la table de faits** (pas de dimension pour l'instant). Une `dim_train_type` pourra être ajoutée plus tard sans changer le grain.
7. **`snapshot_at` et `source_file` sont des colonnes techniques** (audit, lignage vers le bronze), pas des attributs métier.
8. **`dim_date`** : une ligne par jour, **du 01/01/2024 au 31/12/2030** (2 557 jours), remplie une fois pour toutes par upsert ; clé entière `AAAAMMJJ` (lisible, triable, compacte). Sa vraie valeur est ce qui ne se calcule pas : les **jours fériés belges** (bibliothèque `holidays`, version figée par `uv.lock`), puis les vacances scolaires. **`is_holiday` inclut les dimanches de Pâques et de Pentecôte** (la liste de la bibliothèque : 12 jours par an, 84 sur la période) ; pour comparer des jours ouvrables, filtrer aussi sur `is_weekend`.
9. **`dim_station` est en SCD 1** (un upsert met à jour les attributs, la `station_key` ne change jamais). La SCD 2 (historique des noms) viendra avec les snapshots dbt (semaine 3).
10. **L'upsert ne supprime rien** : il est idempotent pour les lignes qu'il charge, mais ne nettoie pas celles qu'il ne charge plus (voulu pour `dim_station` : une gare disparue d'iRail garde ses anciens départs).
11. **Le membre « gare inconnue » (`station_key = -1`)** existe dans `dim_station`. Un départ dont la gare (départ ou destination) est absente de la dimension est **chargé quand même** avec la clé `-1` : le pipeline ne s'arrête pas, aucun fait n'est perdu, la clé étrangère est respectée. Le chargement **logue clairement** (niveau `WARNING`) le nombre de faits rattachés au `-1` et les `station_id` concernés, pour les traiter plus tard (relancer `irail-stations`, puis recharger). Un contrôle qualité les compte (bloc D).
12. **`dim_time`** est ajoutée dès maintenant pour l'analyse par tranche horaire ; la clé est calculée, comme la date, **dans le fuseau de Bruxelles** à partir de `scheduled_at`. **Grain atomique : une ligne par minute** (1 440 lignes), clé `time_key = heure × 100 + minute` (`830` = 08 h 30). La règle des tranches est **définie par la fonction `time_band` de `calendar_dim.py`** (source de vérité), en intervalles `[début, fin)` : `night` 0–6 h · `morning_peak` 6–9 h · `morning` 9–12 h · `noon` 12–14 h · `afternoon` 14–17 h · `evening_peak` 17–20 h · `evening` 20–24 h ; `is_peak` = les deux pointes.
