# irail-ingestion

Collects live departure boards of Belgian railway stations from the [iRail API](https://docs.irail.be/), keeps every raw response, and turns them into a clean table of departures that can be queried in SQL to measure SNCB punctuality.

## Why

iRail only shows what is happening now: a liveboard lists the next trains of a station with their current delay, and there is no way to ask for yesterday's board. To study punctuality over days or weeks, the history has to be built on our side. This project does that in two steps:

1. take a snapshot of each station's board every few minutes and store it untouched;
2. once a day, clean those snapshots into one row per departure.

It is also the first part of a larger training project (SNCB punctuality, from API to Power BI), so the code is written the way I would write it in a team: tests, typed data contract, reproducible environment.

## How it works

```
iRail API ──irail-ingestion──▶ bronze (raw JSON) ──irail-transform──▶ silver (Parquet) ──▶ SQL (DuckDB)
            every 10 min          one file per station             one row per departure
                                  and per call                     partitioned by day
```

- **Bronze** (`data/raw/liveboard/date=YYYY-MM-DD/<station>_<timestamp>.json`): the API response exactly as received. Append-only, never modified.
- **Silver** (`data/silver/departures/date=YYYY-MM-DD/departures.parquet`): 15 typed columns, sentinel values turned into NULL, and one row per departure. The same train is seen in several snapshots, so only the latest one is kept (natural key: departure station, vehicle, scheduled time). The full contract is in [`docs/silver-schema.md`](docs/silver-schema.md).
- **Analysis**: DuckDB reads the Parquet files directly. First queries are in [`docs/analysis/first-insights.sql`](docs/analysis/first-insights.sql).

## Quick start

Requirements: Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:sanneau/irail-ingestion.git
cd irail-ingestion
uv sync
cp .env.example .env               # then edit the stations / User-Agent if needed
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

Run the analysis:

```bash
uv run python -c "import duckdb; duckdb.sql(\"SELECT * FROM 'data/silver/departures/*/*.parquet' LIMIT 5\").show()"
```

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

## Tests and quality

```bash
uv run pytest              # 22 tests, about 1 second, no network
uv run ruff check .
uv run pre-commit run --all-files
```

- Conversion rules (strict text → int / bool / UTC datetime, sentinel values) have unit tests.
- The silver job is tested end to end in a temporary folder: output written in the right partition, idempotence (running a day twice gives one file with the same content), invalid date rejected.
- The HTTP client is tested without calling iRail (`responses`): a 400 is not retried, a 500 followed by a 200 succeeds after one retry, repeated 500s give up after the maximum number of attempts.
- pre-commit runs ruff and a few safety checks (private keys, large files) before every commit.

## Project layout

```
src/irail_ingestion/
├── config.py           settings loaded from environment variables
├── logging_config.py   logging configured once, at the entry point
├── exceptions.py       domain errors (transient vs. invalid request vs. invalid response)
├── client.py           HTTP session, retries with exponential backoff, response validation
├── bronze_storage.py   bronze paths and raw JSON writer
├── ingest_job.py       irail-ingestion entry point
├── models.py           Departure: the silver row
├── transform.py        pure conversion functions, typed DataFrame, deduplication
├── silver_storage.py   reads a bronze partition, writes the silver Parquet
└── transform_job.py    irail-transform entry point
tests/                  pytest suite
docs/                   API exploration notes, silver contract, analysis queries
```

## Design choices

- **Keep the raw data.** Bronze is never rewritten, so the silver layer can be rebuilt at any time if a rule changes.
- **Contract first.** The silver columns, types and conversion rules were written down and checked against four days of real data before any code.
- **Fail on bad input, not on one bad file.** A value that does not match the contract rejects the row (with its reason) instead of being guessed. A broken bronze file is logged and skipped; the job fails only if too many rows are rejected or nothing was read.
- **Idempotent jobs.** One fixed file per silver partition: re-running a day overwrites it instead of adding duplicates.
- **Retries only where they make sense.** Timeouts, 429 and 5xx are retried with exponential backoff and jitter; 4xx and malformed responses are not.

## Known limitations

- The delay stored is the last delay announced before departure, not the real delay at arrival (the liveboard only lists trains that have not left yet).
- Overwriting a Parquet file is not atomic. A table format such as Delta Lake would fix this.
- Partitions follow the snapshot date in UTC, so a departure around midnight could in theory appear in two days.
- `irail-transform` loads the full settings, including the API ones it does not use. Storage and API configuration should be split.
- The data collected so far covers a few days, with gaps at night: the numbers in `docs/analysis` are exploratory.

## Roadmap

- [x] Ingestion into a bronze layer, with retries and validation
- [x] Silver layer (typed, deduplicated Parquet) and first SQL analysis
- [x] Test suite, API mocks, pre-commit
- [ ] Star schema in PostgreSQL (Docker), station dimension from the `stations` endpoint
- [ ] dbt models (staging → marts) with tests
- [ ] Databricks / Delta Lake medallion layers
- [ ] Azure: Data Lake Storage, Data Factory, infrastructure as code with Terraform
- [ ] CI with GitHub Actions, Power BI report
