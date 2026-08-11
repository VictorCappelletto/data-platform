# Architecture

## Goals

Build a **portfolio-ready** data platform that shows how multiple products share the same foundation (utils, lake paths, secrets, DQ, CI), with clear medallion layers and thin orchestration.

## Shared libs

| Package | Responsibility |
|---------|----------------|
| `platform_utils` | Structured logging, retry, date windows |
| `platform_dbutils` | `LayerPaths`, `LakeIO`, optional `get_spark()` |
| `platform_secrets` | `get_secret()` from env or AWS Secrets Manager |
| `platform_dq` | Pluggable checks + `run_checks()` gate |

Products never hardcode lake roots or secret backends — they call the libs.

## Products

| Product | Layers | Notes |
|---------|--------|-------|
| `hdl_ingest` | landing → bronze → silver | `LakeTable` contract + `OrdersTable` with `is_current` |
| `kpi_metrics` | silver → gold | Demo KPIs for `br_demo` |
| `analytics_export` | gold → export | Fails pipeline if DQ fails |

## Orchestration

Airflow DAGs only call product entrypoints (`run_landing`, `run_kpi_pipeline`, `run_export`). Business logic stays in products — same idea as enterprise “workflow JSON + notebook/code”, adapted to Airflow.

## Environments

| Env | Backend | Secrets |
|-----|---------|---------|
| `local` | filesystem under `LAKE_ROOT` | `.env` |
| `dev` / `prod` | S3 (`s3a://bucket/env/layer/...`) | AWS Secrets Manager |

## What this is not

- Not a copy of any employer repository
- Not production multi-country streaming
- Synthetic seeds only
