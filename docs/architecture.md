# Architecture

## Goals

Portfolio-ready data platform with:
- **Shared SDK** in `src/dataplatform/`
- **Isolated apps** in `apps/` (pattern from frontline-force `notebooks/<app>/`)
- **Single config convention**: global `config/`, per-app `apps/<id>/config/`
- Thin Airflow orchestration via `dags/factory.py`

## Comparison with frontline-force-data-platform

| Frontline Force | This repo |
|-----------------|-----------|
| `notebooks/frontline-force-dm-app/` | `apps/medalion_ingestion_project/` |
| `pipelines/.../configs/databricks/` | `apps/.../config/dags/` |
| Domain config inside notebooks (`kpi/config/`) | `apps/.../config/products/` |
| Databricks job JSON | Airflow YAML + thin Python DAGs |

## Config layers

| Layer | Path | Role |
|-------|------|------|
| Platform | `config/platform/{env}.yml` | Lake root, secrets, logging |
| Global constants | `config/constants.yml` | Medallion layer names |
| App | `apps/<id>/config/app.yml` | App id, lake prefix, brewery/orders |
| Product | `apps/<id>/config/products/*.yml` | Domain tables, DQ, KPIs |
| DAG | `apps/<id>/config/dags/*.yml` | Schedule, tasks, pools |
| App constants | `apps/<id>/config/constants.yml` | KPI, brewery, pools |

`ConfigLoader(app=...)` merges global + app config. Env vars override YAML (`LAKE_ROOT`, `DATA_PLATFORM_APP`).

## Code layout

| Module | Responsibility |
|--------|----------------|
| `dataplatform.config` | YAML loader, `PlatformSettings`, `AppSettings` |
| `dataplatform.dbutils` | `LayerPaths`, `LakeIO`, Spark |
| `dataplatform.dq` | Checks + gate |
| `apps/<id>/src/<package>/` | Pipelines extending `ProjectProductBase` |

## Active app: `medalion_ingestion_project`

| Product | Layers |
|---------|--------|
| `hdl_ingest` | landing → bronze → silver |
| `kpi_metrics` | silver → gold |
| `analytics_export` | gold → export + DQ |
| `brewery_etl` | partitioned medallion |

Lake path: `{lake_root}/{env}/medalion_ingestion_project/{layer}/{domain}/{table}/`

## Orchestration

- `dags/factory.py` reads `apps/<id>/config/dags/*.yml`
- `apps/<id>/dags/*_dag.py` call `build_dag_from_yaml(dag_id, app=...)`
- Docker mounts app DAGs at `/opt/airflow/dags/<app_id>/`

## Environments

| Env | Config | Backend |
|-----|--------|---------|
| `local` | `config/platform/local.yml` | filesystem |
| `dev` | `config/platform/dev.yml` | S3 |
| `prod` | `config/platform/prod.yml` | S3 |

App-specific overrides live in `apps/<id>/config/app.yml` under `environments:`.

## Adding another app

Copy `apps/medalion_ingestion_project/`, update `config/app.yml`, set `DATA_PLATFORM_APP`. No changes to existing apps or global SDK required.
