# Databricks notebooks: the medallion in Delta Lake

- `incremental.py`: bronze JSON → silver (explode, typing, window dedup on the grain) → gold punctuality, with an idempotent `MERGE` and a 3-day lookback (replaying the batch: 0 inserted, 0 updated, silver stays at 2,445 rows).
- `streaming.py`: Auto Loader (`cloudFiles`, `availableNow`) from the Volume into a bronze table; the checkpoint reads only new files (1,800 → 0 new on rerun → 2,535 after adding a day).
- `partitionnement.py`: Spark partitions on read, `repartition` vs `coalesce`, shuffle in `explain()`, `OPTIMIZE` (2 files → 1), and why partitioning by a high-cardinality column is a trap.
- Tables live in Unity Catalog, one schema per layer: `workspace.bronze`, `workspace.silver`, `workspace.gold`.
