# medalion_ingestion_project

App demo de ingestão medallion: **orders** (HDL → KPI → export) e **brewery** (API/fixture → DQ → gold).

## Estrutura

```text
medalion_ingestion_project/
├── config/
│   ├── app.yml                      # identidade do app (id, lake prefix)
│   ├── constants.yml                # KPI, brewery DQ, pools
│   ├── extraction/
│   │   └── config_extraction.yml    # API/fixture brewery
│   ├── ingestion/
│   │   └── config_ingestion.yml     # orders + brewery medallion ingest
│   ├── transformation/
│   │   └── config_transformation.yml # KPI, export, brewery DQ/gold
│   └── dags/                        # definição YAML de cada DAG Airflow
├── src/medalion_ingestion_project/
│   ├── extraction/                  # extração de fontes externas
│   │   ├── brewery.py
│   │   └── scripts/run_brewery.py
│   ├── ingestion/                   # landing → bronze → silver
│   │   ├── orders/
│   │   ├── brewery/
│   │   └── scripts/run_orders.py, run_brewery.py
│   └── transformation/              # KPIs, export, DQ → gold
│       ├── kpi.py, export.py
│       ├── brewery/
│       └── scripts/run_kpi.py, run_export.py, run_brewery.py
├── dags/                            # wrappers Airflow
└── seeds/                           # dados de entrada do demo
```

## Processos

| Processo | Domínio | O que faz |
|----------|---------|-----------|
| **extraction** | brewery | API Open Brewery ou fixture JSON |
| **ingestion** | orders | seed CSV → landing → bronze → silver |
| **ingestion** | brewery | extract → landing → bronze → silver (particionado) |
| **transformation** | kpi | silver orders → gold KPIs |
| **transformation** | analytics_export | gold KPIs → export + DQ |
| **transformation** | brewery | DQ checks → gold |

Config por processo: `config/<processo>/config_<processo>.yml`

## Seeds

| Arquivo | Processo | Rows |
|---------|----------|------|
| `seeds/orders_raw.csv` | ingestion/orders | 6 pedidos → 5 `is_current` em silver |
| `seeds/breweries_sample.json` | extraction/brewery | 4 registros → 3 após dedup |

## Rodar localmente

```bash
# Por processo (dentro do app)
python apps/medalion_ingestion_project/src/medalion_ingestion_project/ingestion/scripts/run_orders.py
python apps/medalion_ingestion_project/src/medalion_ingestion_project/transformation/scripts/run_kpi.py

# Cadeia completa (repo root)
python scripts/run_demo_pipeline.py      # orders
python scripts/run_brewery_demo.py       # brewery
```
