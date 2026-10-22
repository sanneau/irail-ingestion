#!/usr/bin/env bash
# Charge le Data Vault (schéma dv) pour TOUS les jours de la silver.
#
# Pourquoi jour par jour : data_vault_load.sql lit stg_departure, et ce staging ne contient
# qu'UN jour (irail-load-facts le vide puis le remplit à chaque lancement). Il faut donc,
# pour chaque jour : remplir le staging, PUIS charger le Data Vault depuis lui.
#
# Ce que lance ce script, pour un jour :
#
#   load_data_vault.sh
#     ├─ irail-load-facts <jour>      job Python (load_facts_job.py), via uv
#     │    silver Parquet du jour ──▶ stg_departure (vidé puis rempli)
#     │                           ──▶ fact_departure (upsert, lookup des clés de dim_station)
#     │                           ──▶ etl_load_log (une ligne "success" ou "failed")
#     └─ psql < sql/data_vault_load.sql   SQL exécuté dans le conteneur PostgreSQL
#          stg_station + stg_departure ──▶ dv.hub_*, dv.link_departure, dv.sat_* (insert-only)
#
# Solution provisoire : le Data Vault dépend du staging de l'étoile.
# Cible (S3, dbt) : charger le Data Vault directement depuis la silver.
#
# Lancer depuis la racine du repo : ./scripts/load_data_vault.sh
# Relançable : un 2e lancement ne change aucun comptage.

# -e : arrêter au 1er échec (sinon le Data Vault serait chargé depuis le staging d'un AUTRE jour)
# -u : erreur si une variable n'existe pas · -o pipefail : un échec au milieu d'un | compte aussi
set -euo pipefail

# Raccourci : exécuter psql DANS le conteneur pgdatabase.
# -T : pas de terminal interactif, pour pouvoir lui envoyer un fichier avec <
PSQL="docker compose exec -T pgdatabase psql -U irail -d sncb_bruxelles"

echo "Etape 1 : structure du Data Vault (sql/data_vault.sql)"
# CREATE ... IF NOT EXISTS : ne fait rien si les tables existent déjà ; la vue est recréée.
$PSQL < sql/data_vault.sql

echo "Etape 2 : pour chaque jour de la silver, remplir stg_departure puis charger le Data Vault"
# ls liste les dossiers date=AAAA-MM-JJ (dans l'ordre, grâce au format ISO) ; sed enlève "date=".
for d in $(ls data/silver/departures | sed 's/date=//'); do
    echo "--- $d"
    # ① Python : silver du jour -> stg_departure -> fact_departure (+ journal)
    uv run --env-file .env irail-load-facts "$d"
    # ② SQL : stg_departure (ce jour-là) -> hubs, link, satellites
    $PSQL < sql/data_vault_load.sql
done

echo "Etape 3 : controle (attendu : links = faits)"
$PSQL -c "select (select count(*) from fact_departure) faits, (select count(*) from dv.link_departure) links, (select count(*) from dv.sat_departure) sat_dep, (select count(*) from dv.hub_station) hub_st, (select count(*) from dv.hub_vehicle) hub_veh;"

echo "--END--"
