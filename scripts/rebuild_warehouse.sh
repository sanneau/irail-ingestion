#!/usr/bin/env bash
set -euo pipefail

echo "Etape 1 : la base"
docker compose up -d --wait

echo "Etape 2: Création des station"
uv run --env-file .env irail-load-stations

echo "Etape 3: Création de la dimensions date et time"
uv run --env-file .env irail-load-dates

# Pas de irail-load-facts --missing ici : load_data_vault.sh lance déjà irail-load-facts
# pour chaque jour (il en a besoin pour remplir stg_departure). L'appeler ici aussi
# chargerait les faits deux fois.
echo "Etape 4: Création des faits (fact_departure) et du Data Vault"
./scripts/load_data_vault.sh

echo "Etape 5: Controle Qualité"
docker compose exec -T pgdatabase psql -U irail -d sncb_bruxelles < sql/quality_checks.sql

echo "--END--"
