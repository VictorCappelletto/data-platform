# Architecture audit — code model & reference alignment

Audit date: 2026-08-13  
References: [README.md](../README.md), [architecture.md](./architecture.md), [Curso_Pipeline_Azure1](https://github.com/VictorCappelletto/Curso_Pipeline_Azure1)

---

## Scorecard

| App | Code model (GROW/frontline) | Curso_Pipeline_Azure1 | Verdict |
|-----|----------------------------|------------------------|---------|
| `medalion_ingestion_project` | **9/10** | N/A | Reference implementation |
| `ingestion_azure` | **9/10** (after scaffold) | **8/10** | Aligned; Databricks/Synapse substituted |

---

## Code model checklist

| Rule | medalion | ingestion_azure |
|------|----------|-----------------|
| `config/<processo>/config_*.yml` | ✅ | ✅ extraction, ingestion, transformation, consumption |
| `base.py` per process | ✅ | ✅ + `consumption/base.py` |
| `orchestrator/` thin entry points | ✅ | ✅ `orchestrator/{extraction,ingestion,transformation,consumption}.py` |
| `config/orchestration/*.yml` | ✅ | ✅ `extraction`, `transformation`, `consumption` |
| `config/workflows/*.yml` | ✅ | ✅ |
| `workflows/orchestrator_base.py` | ✅ | ✅ |
| `workflows/runs/*.py` | ✅ | ✅ 1 runner por processo + `olist_demo.py` |
| `runtime.py` bootstrap | ✅ | ✅ |
| Domain logic not in orchestrator | ✅ | ✅ |
| Tests + workflow imports | ✅ | ✅ |

---

## Curso_Pipeline_Azure1 mapping

| Componente original | Implementação | Status |
|--------------------|---------------|--------|
| SQL Server (fonte) | Docker `olist` | ✅ |
| ADF copy → landing | `pl_olist_landing_copy` + SHIR | ✅ |
| ADLS landing/processing/curated | `stolist*` containers | ✅ |
| Databricks notebook | `transformation/*` + PySpark local | ✅ substituído |
| `customers_db` SQL tables | `transformation/olist.py` | ✅ |
| Synapse serverless | `olist_dw` (SQL Server) | ✅ substituído |
| Power BI | `consumption/sql_server_publish.py` + doc | ⚠️ manual |
| Orquestração Python | `orchestrator/*.py` (1 por processo) | ✅ |

Notebook → módulo: [olist-databricks-mapping.md](./olist-databricks-mapping.md)

---

## Remaining gaps (non-blocking)

### `medalion_ingestion_project`

| Gap | Severity | Notes |
|-----|----------|-------|
| KPI metrics hardcoded vs YAML | Medium | `transformation/kpi.py` ignores `config_transformation.yml` metrics block |
| DAG builders use `project=` alias | Low | Prefer `app=` in `workflows/*_dag.py` |
| Demo runners skip orchestrator | Low | `workflows/runs/orders_demo.py` calls domain directly |

### `ingestion_azure`

| Gap | Severity | Notes |
|-----|----------|-------|
| `landing_export.py` under `ingestion/` with `PROCESS=extraction` | Low | Works; folder vs process name mismatch |
| Legacy `ingestion/orders.py` | Low | Mark deprecated; uses old medallion Layer paths |
| Dual lake naming (ADLS zones vs classic medallion) | Low | Documented — Olist uses landing/processing/curated on lake, bronze/silver/gold on SQL |
| Airflow not mounted for `ingestion_azure` DAGs | Low | DAG modules exist; add to docker-compose when needed |
| `.pbix` versionado | Low | Power BI connect manual |

---

## Orchestration entry points (ingestion_azure)

| Task | Orchestrator | Domain |
|------|--------------|--------|
| `landing_export` | `orchestrator.extraction:run_landing_export` | `ingestion.landing_export:run_landing_export` |
| `processing` | `orchestrator.transformation:run_processing` | `transformation.olist:run_write_processing` |
| `curated` | `orchestrator.transformation:run_curated` | `transformation.olist:run_curated` |
| `publish_sql` | `orchestrator.consumption:run_publish_sql` | `consumption.sql_server_publish:run_publish_curated` |
| `sql_catalog` | `orchestrator.transformation:run_sql_catalog` | `transformation.olist:run_sql_catalog` |

**Local runner:**

```powershell
set DATA_PLATFORM_APP=ingestion_azure
python apps/ingestion_azure/workflows/runs/olist_demo.py --mode full
python apps/ingestion_azure/workflows/runs/olist_demo.py --mode transform_from_landing
python apps/ingestion_azure/workflows/runs/olist_demo.py --mode publish
```

**Azure (via Make):**

```powershell
make azure-adf-trigger              # ADF → landing (external orchestrator)
make azure-olist-transform          # transform_from_landing
make azure-olist-publish-sql        # publish
```

---

## Conclusion

Both apps now follow the **three-layer pattern** (workflow YAML → orchestrator → domain) documented in `architecture.md`. The Olist Azure pipeline respects the **data flow** of Curso_Pipeline_Azure1 with deliberate substitutions (local PySpark, SQL Server `olist_dw`) for portfolio cost control.

Next optional hardening: wire KPI YAML in medalion, deprecate `ingestion/orders.py`, mount `ingestion_azure` DAGs in Airflow compose.
