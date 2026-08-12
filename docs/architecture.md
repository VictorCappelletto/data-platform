# Architecture

## Goals

Portfolio-ready data platform with:
- **Shared SDK** in `src/dataplatform/`
- **Isolated apps** in `apps/` (pattern from frontline-force `notebooks/<app>/`)
- **Single config convention**: global `config/`, per-app `apps/<id>/config/`
- Thin Airflow orchestration via `dags/factory.py`

## Comparison with frontline-force-data-platform

| Frontline Force | This repo | GROW |
|-----------------|-----------|------|
| `notebooks/frontline-force-dm-app/` | `apps/medalion_ingestion_project/` | `projects/grow/` |
| `pipelines/.../configs/databricks/` | `apps/.../config/dags/` | `workflows/workflow_jsons/` |
| Domain config inside notebooks | `apps/.../config/<processo>/` | `configs/<processo>/` |
| Databricks job JSON | Airflow YAML + thin Python DAGs | `workflows/*.json` |
| — | `apps/.../orchestrator/` | `orchestrator/*.ipynb` |
| — | `apps/.../config/orchestration/` | task registry in workflow JSON |

## Config layers

| Layer | Path | Role |
|-------|------|------|
| Platform | `config/platform/{env}.yml` | Lake root, secrets, logging |
| Global constants | `config/constants.yml` | Medallion layer names |
| App | `apps/<id>/config/app.yml` | App id, lake prefix |
| Process | `apps/<id>/config/<processo>/config_<processo>.yml` | Domínios por etapa (extraction, ingestion, transformation) |
| Orchestration | `apps/<id>/config/orchestration/*.yml` | Tabela task → orchestrator → domain module |
| DAG | `apps/<id>/config/dags/*.yml` | Schedule, tasks (`orchestrator:` entry points) |
| App constants | `apps/<id>/config/constants.yml` | KPI, brewery, pools |

`ConfigLoader(app=...)` merges global + app config. Env vars override YAML (`LAKE_ROOT`, `DATA_PLATFORM_APP`).

## Code layout

| Module | Responsibility |
|--------|----------------|
| `dataplatform.config` | YAML loader, `PlatformSettings`, `AppSettings` |
| `dataplatform.dbutils` | `LayerPaths`, `LakeIO`, Spark |
| `dataplatform.dq` | Checks + gate |
| `apps/<id>/src/<package>/` | Pipelines por processo (`extraction/`, `ingestion/`, `transformation/`) |
| `apps/<id>/orchestrator/` | Entry points finos — Airflow/CLI chama aqui, não o domínio direto |

## Orchestration (padrão GROW)

Três camadas separadas, como no GROW:

| Camada | GROW | Este repo |
|--------|------|-----------|
| Workflow (DAG) | `workflows/workflow_jsons/*.json` | `config/dags/*.yml` |
| Orchestrator (front door) | `orchestrator/*.ipynb` | `orchestrator/**/*.py` |
| Domain (lógica) | `projects/grow/<domain>/` | `src/<processo>/` |

`config/orchestration/<workflow>.yml` documenta o mapeamento:

```yaml
tasks:
  landing:
    orchestrator: orchestrator.orders.landing:run
    domain_module: medalion_ingestion_project.ingestion.orders.pipeline:run_landing
```

Airflow (`dags/factory.py`) importa apenas `orchestrator.*:run`. O orchestrator faz bootstrap e delega ao módulo de domínio.

## Active app: `medalion_ingestion_project`

| Processo | Domínio | Layers |
|----------|---------|--------|
| extraction | brewery | API/fixture → raw records |
| ingestion | orders | landing → bronze → silver |
| ingestion | brewery | landing → bronze → silver (particionado) |
| transformation | kpi | silver → gold |
| transformation | analytics_export | gold → export + DQ |
| transformation | brewery | silver → DQ → gold |

Lake path: `{lake_root}/{env}/medalion_ingestion_project/{layer}/{domain}/{table}/`

## Orchestration

- `config/dags/*.yml` — grafo do workflow (schedule, dependências, pools)
- `config/orchestration/*.yml` — registro task → orchestrator → domain module
- `orchestrator/` — scripts Python finos executados pelo Airflow
- `dags/factory.py` lê DAG YAML e importa `orchestrator.*:run`
- `apps/<id>/dags/*_dag.py` chamam `build_dag_from_yaml(dag_id, app=...)`

## Environments

| Env | Config | Backend |
|-----|--------|---------|
| `local` | `config/platform/local.yml` | filesystem |
| `dev` | `config/platform/dev.yml` | S3 |
| `prod` | `config/platform/prod.yml` | S3 |

App-specific overrides live in `apps/<id>/config/app.yml` under `environments:`.

## Adding another app

Copy `apps/medalion_ingestion_project/`, update `config/app.yml`, set `DATA_PLATFORM_APP`. No changes to existing apps or global SDK required.
