# irail-ingestion

Collects live departure boards of Belgian railway stations from the [iRail API](https://docs.irail.be/), keeps every raw response, turns them into a clean table of departures, and loads them into a PostgreSQL warehouse (a Kimball star schema and a Data Vault) to measure SNCB punctuality.

## Why

iRail only shows what is happening now: a liveboard lists the next trains of a station with their current delay, and there is no way to ask for yesterday's board. To study punctuality over days or weeks, the history has to be built on our side. This project does that in three steps:

1. take a snapshot of each station's board every few minutes and store it untouched;
2. once a day, clean those snapshots into one row per departure;
3. load the clean rows into a warehouse modelled for analysis.

It is also the first part of a larger training project (SNCB punctuality, from API to Power BI), so the code is written the way I would write it in a team: tests, typed data contract, reproducible environment.

## How it works

```
iRail API ──irail-ingestion──▶ bronze (raw JSON) ──irail-transform──▶ silver (Parquet) ──irail-load-*──▶ PostgreSQL
            every 10 min          one file per station             one row per departure            star schema (public)
                                  and per call                     partitioned by day               + Data Vault (dv)
```

- **Bronze** (`data/raw/liveboard/date=YYYY-MM-DD/<station>_<timestamp>.json`): the API response exactly as received. Append-only, never modified.
- **Silver** (`data/silver/departures/date=YYYY-MM-DD/departures.parquet`): 15 typed columns, sentinel values turned into NULL, and one row per departure. The same train is seen in several snapshots, so only the latest one is kept (natural key: departure station, vehicle, scheduled time). The full contract is in [`docs/silver-schema.md`](docs/silver-schema.md).
- **Warehouse** (PostgreSQL 18 in Docker):
  - a **star schema** for analysis: `fact_departure` (one row per departure), `dim_station` (SCD type 2), `dim_date` (with Belgian public holidays) and `dim_time` (one row per minute, with peak bands). Design in [`docs/star-schema.md`](docs/star-schema.md);
  - a **Data Vault** in the `dv` schema, built next to the star to compare both methods: hubs, a link and satellites, insert-only, with a `dim_station` view rebuilt from it. Design in [`docs/data-vault.md`](docs/data-vault.md);
  - a load log (`etl_load_log`): one `success` or `failed` row per loaded day, used to load only the missing days.
- **Analysis**: DuckDB reads the Parquet files directly ([`docs/analysis/`](docs/analysis/)); the warehouse is queried with any PostgreSQL client (pgAdmin is included).

### Job map

| Command | Reads | Writes |
|---|---|---|
| `irail-ingestion` | iRail `/liveboard` | bronze liveboard JSON |
| `irail-transform <day>` | bronze of that day | silver `departures` Parquet of that day |
| `irail-stations` | iRail `/stations` | bronze stations JSON, silver `stations.parquet` |
| `irail-load-stations` | silver `stations.parquet` | `stg_station` → `dim_station` (SCD 2) |
| `irail-load-dates` | nothing (calendar computed in Python) | `dim_date`, `dim_time` |
| `irail-load-facts <day>` / `--missing` | silver `departures`, `dim_station` | `stg_departure` → `fact_departure`, `etl_load_log` |
| `sql/data_vault_load.sql` | `stg_station`, `stg_departure` | `dv.hub_*`, `dv.link_departure`, `dv.sat_*` |
| `scripts/load_data_vault.sh` | every silver day | runs `irail-load-facts` then `data_vault_load.sql`, day by day |
| `scripts/rebuild_warehouse.sh` | everything above | the whole warehouse, then the quality checks |

## Quick start

Requirements: Python 3.13, [uv](https://docs.astral.sh/uv/) and Docker (with Compose).

```bash
git clone git@github.com:sanneau/irail-ingestion.git
cd irail-ingestion
uv sync
cp .env.example .env               # then edit the stations, User-Agent and database passwords
uv run pre-commit install          # once per clone
```

Collect a snapshot of every configured station (bronze):

```bash
uv run --env-file .env irail-ingestion
```

Build the silver table for one day (the date is required, in UTC):

```bash
uv run --env-file .env irail-transform 2026-09-26
```

Run the analysis on the silver files:

```bash
uv run python -c "import duckdb; duckdb.sql(\"SELECT * FROM 'data/silver/departures/*/*.parquet' LIMIT 5\").show()"
```

### Build the warehouse

From the root of the repository, one command rebuilds everything from the silver files (database, dimensions, facts, Data Vault, quality checks):

```bash
./scripts/rebuild_warehouse.sh
```

It is safe to run again: every load is an upsert or an insert-only step, so a second run changes no count. The full rebuild was checked by deleting the database (`docker compose down -v`) and rebuilding it: same counts (12,606 departures over 15 days, 715 stations), quality checks empty.

pgAdmin runs on <http://localhost:8085>. Register the server with host `pgdatabase` (the Compose service name, not `localhost`), port `5432`, database `sncb_bruxelles`.

### Configuration

Everything that changes between environments comes from environment variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `IRAIL_BASE_URL` | required | API root, e.g. `https://api.irail.be/v1` |
| `IRAIL_USER_AGENT` | required | identifies the client, as requested by iRail |
| `IRAIL_STATION_IDS` | required | comma-separated station ids |
| `IRAIL_DATA_DIR` | `data/raw` | bronze folder |
| `IRAIL_SILVER_DIR` | `data/silver` | silver folder |
| `IRAIL_TIMEOUT_S` | `10` | HTTP timeout per call |
| `DB_HOST`, `DB_PORT`, `DB_NAME` | required | database seen from the host: `localhost`, `5432`, `sncb_bruxelles` |
| `DB_USER`, `DB_PASSWORD` | required | PostgreSQL user (also used by Docker Compose to create it) |
| `DB_EMAIL`, `DB_ADMIN_PASSWORD` | required | pgAdmin login |

Secrets stay in `.env`, which is never committed.

## Tests and quality

```bash
uv run pytest              # 87 tests, a few seconds, no network and no database
uv run ruff check .
uv run pre-commit run --all-files
```

- Conversion rules (strict text → int / bool / UTC datetime, sentinel values) have unit tests.
- The silver job is tested end to end in a temporary folder: output written in the right partition, idempotence (running a day twice gives one file with the same content), invalid date rejected.
- The HTTP client is tested without calling iRail (`responses`): a 400 is not retried, a 500 followed by a 200 succeeds after one retry, repeated 500s give up after the maximum number of attempts.
- The warehouse code is tested without PostgreSQL: row conversion, calendar rules (holidays, time bands), the choice of missing days, and the failure path of a load (the database is replaced by a fake that fails; the test checks the return code, the `failed` row in the load log and the day in the error message).
- `sql/quality_checks.sql` runs on the real warehouse after each rebuild. Each check returns the faulty rows, so an empty result means OK: unique grain, no unknown station, date and time keys consistent with the Brussels time zone, one current version per station, no gap or overlap between versions.
- GitHub Actions runs ruff and the tests on every push and pull request; pre-commit runs ruff and a few safety checks (private keys, large files) before every commit.

## Project layout

```
src/irail_ingestion/
├── config.py            settings loaded from environment variables (API, folders, database)
├── logging_config.py    logging configured once, at the entry point
├── exceptions.py        domain errors (transient vs. invalid request vs. invalid response)
├── client.py            HTTP session, retries with exponential backoff, response validation
├── bronze_storage.py    bronze paths and raw JSON writer
├── ingest_job.py        irail-ingestion entry point
├── models.py            Departure: the silver row
├── transform.py         pure conversion functions, typed DataFrame, deduplication
├── silver_storage.py    reads a bronze partition, writes the silver Parquet
├── transform_job.py     irail-transform entry point
├── stations_job.py      irail-stations entry point (station list → bronze and silver)
├── calendar_dim.py      dim_date and dim_time rows (holidays, ISO week, time bands)
├── warehouse.py         table definitions, staging, upserts, SCD 2 merge, load log
├── load_stations_job.py irail-load-stations entry point
├── load_dates_job.py    irail-load-dates entry point
└── load_facts_job.py    irail-load-facts entry point (one day or every missing day)
sql/
├── data_vault.sql       Data Vault tables and the dv.v_dim_station view
├── data_vault_load.sql  insert-only load of hubs, link and satellites from the staging tables
└── quality_checks.sql   checks run after each rebuild (an empty result means OK)
scripts/
├── rebuild_warehouse.sh rebuilds the whole warehouse from the silver files
└── load_data_vault.sh   loads the Data Vault for every silver day
docker-compose.yml       PostgreSQL 18 and pgAdmin, data kept in named volumes
tests/                   pytest suite
docs/                    API notes, silver contract, star schema, Data Vault, analysis queries
```

## Design choices

**Ingestion and silver**

- **Keep the raw data.** Bronze is never rewritten, so the silver layer can be rebuilt at any time if a rule changes.
- **Contract first.** The silver columns, types and conversion rules were written down and checked against four days of real data before any code.
- **Fail on bad input, not on one bad file.** A value that does not match the contract rejects the row (with its reason) instead of being guessed. A broken bronze file is logged and skipped; the job fails only if too many rows are rejected or nothing was read.
- **Idempotent jobs.** One fixed file per silver partition: re-running a day overwrites it instead of adding duplicates.
- **Retries only where they make sense.** Timeouts, 429 and 5xx are retried with exponential backoff and jitter; 4xx and malformed responses are not.

**Warehouse**

- **The grain is a constraint, not a comment.** One row per departure, enforced by `UNIQUE (departure_station_key, scheduled_at, vehicle_id)`; loads are upserts, so reloading a day never creates duplicates.
- **Station history with SCD type 2.** A renamed or moved station gets a new version with semi-open validity intervals (`valid_from` included, `valid_to` excluded). Each departure is linked to the version valid at its scheduled time, so old departures keep the old name.
- **Store instants in UTC, derive business dates in Brussels time.** The date and time keys are computed with `AT TIME ZONE 'Europe/Brussels'`: 30 departures out of 2,843 change day between UTC and Brussels.
- **Never lose a fact.** A departure whose station is missing from the dimension is loaded with the "unknown station" member (`-1`), logged as a warning, and counted by a quality check.
- **A load log drives the catch-up.** `irail-load-facts --missing` compares the silver days with the `success` rows of `etl_load_log` and loads only the difference. A failed day is logged as `failed`, with the day in the error message.
- **A Data Vault next to the star, to compare.** Hash keys (`md5(upper(trim(id)))`) are computed, not looked up, so hubs, link and satellites load without joins; satellites only get a new row when the `hash_diff` changes. The `dv.v_dim_station` view rebuilds the SCD 2 dimension and matches the table exactly (`EXCEPT` both ways returns nothing).
- **The warehouse is disposable.** Everything is rebuilt from the silver files by one script, checked by deleting the database and comparing the counts.

## Known limitations

- The delay stored is the last delay announced before departure, not the real delay at arrival (the liveboard only lists trains that have not left yet).
- Overwriting a Parquet file is not atomic. A table format such as Delta Lake would fix this.
- Partitions follow the snapshot date in UTC, so a departure around midnight could in theory appear in two days.
- `irail-transform` loads the full settings, including the API ones it does not use. Storage and API configuration should be split.
- **Station history is only as good as the station collection.** The station list was collected once, and the silver keeps a single `stations.parquet` without a date. A rebuild therefore gives one version per station: a real rename would be lost. Fix: collect `/stations` every day, partition the silver by day, and replay the versions in order.
- **The Data Vault depends on the star's staging tables.** `stg_departure` only holds the last loaded day, so `load_data_vault.sh` reloads the facts day by day to fill it, and each run adds a second `success` row per day in the load log. The load order (star first, then Data Vault) is also the opposite of the target architecture (Data Vault, then star). Planned fix: load the Data Vault from the silver files with dbt.
- The SQL of the star schema lives in Python strings (`warehouse.py`); it will move to dbt models.
- After `docker compose down -v`, the pgAdmin server has to be registered again (a provisioned `servers.json` would avoid it).
- The data covers 15 days, with gaps at night: the numbers in `docs/analysis` are exploratory.

## Roadmap

- [x] Ingestion into a bronze layer, with retries and validation
- [x] Silver layer (typed, deduplicated Parquet) and first SQL analysis
- [x] Test suite, API mocks, pre-commit, CI
- [x] Star schema in PostgreSQL (Docker): SCD 2 stations, date and time dimensions, load log, quality checks
- [x] Data Vault next to the star, with a dimension view rebuilt from it
- [ ] dbt models (staging → Data Vault → marts) with tests
- [ ] Databricks / Delta Lake medallion layers
- [ ] Azure: Data Lake Storage, Data Factory, infrastructure as code with Terraform
- [ ] Power BI report
