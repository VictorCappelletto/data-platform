# medalion_ingestion_project

App demo de ingestão medallion: **orders** (HDL → KPI → export) e **brewery** (API/fixture → DQ → gold).

## Estrutura

```text
medalion_ingestion_project/
├── config/
│   ├── app.yml
│   ├── constants.yml
│   ├── extraction/config_extraction.yml
│   ├── ingestion/config_ingestion.yml
│   ├── transformation/config_transformation.yml
│   ├── orchestration/              # registro task → orchestrator → domain
│   └── dags/                       # workflow Airflow (schedule, deps)
├── orchestrator/                   # entry points Python (como GROW orchestrator/)
│   ├── orders/                     # landing, bronze, silver
│   ├── brewery/                    # ingestion, dq_gold
│   ├── analytics/                  # kpi_metrics, analytics_export
│   └── workflows/                  # demos locais (orders_demo, brewery_demo)
├── src/medalion_ingestion_project/
│   ├── extraction/
│   ├── ingestion/
│   └── transformation/
├── dags/                           # wrappers Airflow finos
└── seeds/
```

## Camadas (padrão GROW)

| Camada | Pasta | Função |
|--------|-------|--------|
| **Workflow** | `config/dags/` | Grafo Airflow — schedule, dependências, pools |
| **Orchestration** | `config/orchestration/` + `orchestrator/` | Tabela de mapeamento + scripts que o Airflow executa |
| **Domain** | `src/<processo>/` | Lógica de negócio (extraction, ingestion, transformation) |

Exemplo de registro (`config/orchestration/hdl_ingest.yml`):

```yaml
tasks:
  landing:
    orchestrator: orchestrator.orders.landing:run
    domain_module: medalion_ingestion_project.ingestion.orders.pipeline:run_landing
```

## Processos

| Processo | Domínio | O que faz |
|----------|---------|-----------|
| extraction | brewery | API Open Brewery ou fixture JSON |
| ingestion | orders | seed CSV → landing → bronze → silver |
| ingestion | brewery | extract → landing → bronze → silver |
| transformation | kpi | silver orders → gold KPIs |
| transformation | analytics_export | gold KPIs → export + DQ |
| transformation | brewery | DQ checks → gold |

## Rodar localmente

```bash
# Workflow completo (repo root)
python scripts/run_demo_pipeline.py
python scripts/run_brewery_demo.py

# Task individual (orchestrator)
python apps/medalion_ingestion_project/orchestrator/orders/landing.py
python apps/medalion_ingestion_project/orchestrator/analytics/kpi_metrics.py
```
