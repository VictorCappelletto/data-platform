# medalion_ingestion_project

App demo de ingestão medallion: **orders** (HDL → KPI → export) e **brewery** (API/fixture → DQ → gold).

## Estrutura

```text
medalion_ingestion_project/
├── config/
│   ├── workflows/                  # jobs Airflow (schedule, deps)
│   ├── orchestration/              # registro task → orchestrator → domain
│   └── extraction|ingestion|transformation/
├── quality/
│   └── inspect_lake.py             # inspeção do lake (layout, row counts)
├── orchestrator/
│   ├── orders/                     # landing, bronze, silver
│   ├── brewery/                    # ingestion, dq_gold
│   ├── analytics/                  # kpi_metrics, analytics_export
│   └── quality/                    # inspect_lake
├── workflows/                      # módulos Airflow + runs/ (demos locais)
├── extraction/
│   ├── base.py                     # ExtractionBase — HTTP, fixtures, paginação
│   └── brewery.py
├── ingestion/
│   ├── base.py                     # IngestionBase + helpers de partição
│   ├── brewery.py                  # pipeline brewery (flat, sem subpastas)
│   └── orders.py                   # pipeline orders (flat, sem subpastas)
├── transformation/
│   ├── base.py
│   ├── brewery.py, kpi.py, export.py
├── runtime.py, base.py
├── tests/                          # testes do app + SDK
└── seeds/
```

## Camadas (padrão GROW)

| Camada | Pasta | Função |
|--------|-------|--------|
| **Workflow (job)** | `config/workflows/` + `workflows/*_dag.py` | Grafo Airflow |
| **Orchestration** | `config/orchestration/` + `orchestrator/` | Entry points que o Airflow executa |
| **Domain** | `extraction/`, `ingestion/`, `transformation/` | Lógica de negócio (arquivos flat) |

Exemplo de registro (`config/orchestration/hdl_ingest.yml`):

```yaml
tasks:
  landing:
    orchestrator: orchestrator.orders.landing:run
    domain_module: ingestion.orders:run_landing
```

## Rodar localmente

```bash
python apps/medalion_ingestion_project/workflows/runs/orders_demo.py
python apps/medalion_ingestion_project/workflows/runs/brewery_demo.py
python apps/medalion_ingestion_project/orchestrator/quality/inspect_lake.py

# Task individual
python -m orchestrator.orders.landing
python -m orchestrator.analytics.kpi_metrics
```
