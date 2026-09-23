# Contexte
Je me forme au data engineering pour trouver un travail sur bruxelles dans 2 mois(cible : data engineer Azure/Databricks à Bruxelles).
Ce repo fait partie de mon portfolio. Je dois pouvoir expliquer chaque ligne en entretien.

# Projet
Ingestion des données de l'API iRail (trains SNCB) : API → JSON brut → Parquet.
Package Python en src layout : `src/irail_ingestion/`. Point d'entrée : `uv run irail-ingestion`.

# Règles de travail
- Mode apprentissage : explique d'abord le concept, propose une approche,
  puis laisse-moi écrire le code dans tous les cas.
- Ne modifie jamais mon code mais essaye toujours de maximiser ma compréhension et mon apprentissage
- Signale les mauvaises pratiques de data engineering et les bonne pratique pour que je sois top niveau (idempotence, secrets en dur,
  absence de tests, absence de logs).

# Stack
- Python géré avec uv ; lancer les commandes avec `uv run`
- Lint et format : ruff ; tests : pytest
- Ne jamais commiter de secrets ; utiliser un fichier .env ignoré par Git