#!/usr/bin/env bash
set -euo pipefail

echo "Etape 1 : la base"
docker compose up -d --wait

echo "Etape 2: Création des station"
uv run --env-file .env irail-load-stations

echo "Etape 3: Création de la dimensions date et time"
uv run --env-file .env irail-load-dates

echo "Etape 4: Création des fait"
uv run --env-file .env irail-load-facts --missing

echo "Etape 5: Controle Qualité"
docker compose exec -T pgdatabase psql -U irail -d sncb_bruxelles < sql/quality_checks.sql

echo "--END--"
