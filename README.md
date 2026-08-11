# data-platform

Portfolio **data platform monorepo** — shared SDK, isolated apps, config-driven Airflow orchestration, medallion lake.

Inspired by enterprise patterns (GROW + frontline-force app layout).

## Architecture

```text
data-platform/
├── config/                          # global platform config only
│   ├── platform/                    # local | dev | prod
│   ├── constants.yml                # shared medallion layers
│   └── env/                         # optional .env templates per env
├── src/dataplatform/                # shared SDK (dbutils, dq, secrets, config loader)
├── apps/
│   └── medalion_ingestion_project/  # self-contained app (like frontline-force-dm-app)
│       ├── config/                  # app.yml, dags/, products/, constants.yml
│       ├── src/                     # pipeline code
│       ├── dags/                    # thin Airflow DAG modules
│       └── seeds/
├── dags/factory.py                  # shared DAG builder
├── scripts/
└── tests/
```

## Why this layout?

| Before (confusing) | Now (clear) |
|--------------------|-------------|
| `conf/` + `configs/` at root | Single `config/` for global platform |
| `projects/.../configs/` | `apps/.../config/` (singular, inside the app) |
| `project.yml` at app root | `config/app.yml` with everything else |

Each **app** is self-contained. Global infra stays in `config/` + `src/dataplatform/`.

## Config layers

| Layer | Path | Role |
|-------|------|------|
| Platform | `config/platform/{env}.yml` | Lake, secrets, logging |
| App | `apps/<id>/config/app.yml` | App id, lake prefix, domain settings |
| Product | `apps/<id>/config/products/*.yml` | Tables, DQ, KPI definitions |
| DAG | `apps/<id>/config/dags/*.yml` | Schedule, tasks, pools |

## Quick start

```bash
python -m pip install -e ".[dev]"

set DATA_PLATFORM_APP=medalion_ingestion_project   # Windows
# export DATA_PLATFORM_APP=medalion_ingestion_project

python scripts/run_demo_pipeline.py
pytest -q
python scripts/validate_dags.py
python scripts/inspect_lake.py
```

## Docker

```bash
cp .env.example .env
docker compose up -d postgres minio airflow-init airflow-webserver airflow-scheduler
# UI: http://localhost:8080  (admin / admin)
```

## Adding a new app

1. Copy `apps/medalion_ingestion_project/` → `apps/<new_app_id>/`
2. Edit `config/app.yml`
3. Adapt Python package under `src/`
4. Set `DATA_PLATFORM_APP=<new_app_id>`
5. Mount `apps/<new_app_id>/` in `docker-compose.yml`

See [docs/architecture.md](docs/architecture.md) for details.

## License

MIT — Victor Cappelletto
