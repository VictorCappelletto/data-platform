# Brewery ETL

Open Brewery API → medallion lake (`landing → bronze → silver → gold`) with hive-style partitions.

## Run (fixture, no HTTP)

```bash
export LAKE_ROOT=./data/lake PLATFORM_ENV=local
python scripts/run_brewery_demo.py
```

## Partition layout

```text
{layer}/brewery/breweries/country={CC}/state={ST}/load_date={YYYY-MM-DD}/data.json
```

## Airflow schedules (staggered)

| DAG | Schedule | Pool | Purpose |
|-----|----------|------|---------|
| `brewery_ingest` | `0 6 * * *` | `brewery_pool` (1 slot) | landing → bronze → silver |
| `brewery_dq_gold` | `30 7 * * *` | `brewery_pool` (1 slot) | DQ gate → gold |

Both DAGs use `max_active_runs=1` to avoid concurrent cluster load.

## Env vars

| Variable | Default | Description |
|----------|---------|-------------|
| `BREWERY_API_URL` | Open Brewery API v1 | API base URL |
| `BREWERY_PER_PAGE` | 50 | Page size |
| `BREWERY_MAX_PAGES` | 3 | Max pages per run |
| `BREWERY_USE_FIXTURE` | 0 | Use `seeds/breweries_sample.json` |

## Phase 2 (not in v1)

Azure SQL / ADF / Databricks loaders can plug into gold export using the same partition contract.
