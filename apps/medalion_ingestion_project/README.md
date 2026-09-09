# medalion_ingestion_project

App demo de ingestão medallion: **orders** (HDL → KPI → export) e **brewery** (API/fixture → DQ → gold).

## Estrutura (4 processos — como `ingestion_azure`)

```text
medalion_ingestion_project/
├── config/
│   ├── extraction|ingestion|transformation|consumption/
│   ├── orchestration/              # 1 YAML por processo
│   └── workflows/                  # 1 DAG por processo
├── extraction/                     # brewery API / fixture
├── ingestion/                      # brewery + orders
├── transformation/                 # brewery DQ/gold + KPI
├── consumption/                    # analytics export
├── orchestrator/                   # flat — 1 módulo por processo
├── workflows/
│   ├── extraction_dag.py … consumption_dag.py
│   └── runs/                       # 1 runner por processo + medalion_demo.py
├── quality/inspect_lake.py
├── seeds/
└── tests/
```

## Rodar localmente

```powershell
set DATA_PLATFORM_APP=medalion_ingestion_project
pip install -e ".[dev]"

python workflows/runs/ingestion.py
python workflows/runs/transformation.py
python workflows/runs/consumption.py
python workflows/runs/medalion_demo.py --mode orders_full
python workflows/runs/medalion_demo.py --mode brewery_full
python quality/inspect_lake.py
```

## Registro (exemplo)

```yaml
# config/orchestration/ingestion.yml
tasks:
  orders_landing:
    orchestrator: orchestrator.ingestion:run_orders_landing
    domain_module: ingestion.orders:run_landing
```
