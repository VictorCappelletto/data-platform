# Olist pipeline — Databricks notebook mapping

Python port of [Curso_Pipeline_Azure1/Databricks/olist_processing.ipynb](https://github.com/VictorCappelletto/Curso_Pipeline_Azure1/blob/main/Databricks/olist_processing.ipynb).

## Notebook → código

| Notebook (Databricks) | Módulo Python | ADLS zone |
|----------------------|---------------|-----------|
| Mount `/mnt/landing` | `transformation/io.py` (`OlistLakeMount`) | `landing` |
| Mount `/mnt/processing` | `transformation/io.py` | `processing` |
| Mount `/mnt/curated` | `transformation/io.py` | `curated` |
| ADF / SQL → CSV landing | `ingestion/landing_export.py` | `landing` |
| `spark.read.csv` landing | `transformation/olist.py` (`OlistTransformPipeline.read_landing`) | `landing` |
| SQL temp views + `customers_db` | `transformation/olist.py` (`SparkSqlCatalog`) | `processing` / `curated` |
| `df.write.parquet` processing | `transformation/olist.py` (`write_processing`) | `processing` |
| Filter `customer_state == RJ` | `transformation/olist.py` (`run_curated`) | — |
| Filtered parquet + curated CSV | `transformation/olist.py` | `processing` / `curated` |
| Power BI ← SQL tables | `consumption/sql_server_publish.py` | `silver.*` / `gold.*` in `olist_dw` |

## Orquestração

```python
from runtime import bootstrap
bootstrap()
from workflows.runs.olist_demo import run_full
print(run_full())
```

Passos individuais (registry em `config/orchestration/`):

```python
from orchestrator.extraction import run_landing_export
from orchestrator.transformation import run_processing, run_curated
from orchestrator.consumption import run_publish_sql
```

Engine local vs Spark: `OLIST_PROCESSING_ENGINE=local|spark` — branching dentro de `OlistTransformPipeline`.

## Layout local (espelha containers ADLS)

```text
data/lake/local/ingestion_azure/
├── landing/          customers.csv, orders.csv, ...
├── processing/       customers.parquet, orders.parquet, customers_RJ.parquet
└── curated/          customers_RJ.csv
```

Com `OLIST_LAKE_BACKEND=adls` + `AZURE_STORAGE_ACCOUNT`, paths viram `abfss://{zone}@{account}.dfs.core.windows.net/`.

## Datasets (8 tabelas)

Alinhado ao notebook e ao schema SQL local:

- customers, geolocation, order_items, order_payments
- order_reviews, orders, sellers, product_category_name_translation

Config: `config/extraction/config_extraction.yml`, `config/transformation/config_transformation.yml`.
