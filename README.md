# irail-ingestion
Un script qui interroge l'API iRail (départs et retards des trains en gare), sauvegarde les réponses brutes en JSON classées par date (couche bronze), les nettoie et les convertit en Parquet, puis permet d'analyser les retards en SQL avec DuckDB. Le tout testé (pytest), vérifié (ruff, pre-commit) et lançable en une commande.

## Pourquoi ce projet
Ce projet a pour but de démontrer mes connaissance et compétence dans un projet visible par tout un chacun

## Architecture          
API → JSON brut → Parquet → DuckDB

## Stack technique
Python, uv, pytest
dev : ruff, pre-commit

## Installation
uv sync

## Utilisation
uv run irail-ingestion

## Roadmap
