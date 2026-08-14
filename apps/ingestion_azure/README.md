# Ingestion Azure — Olist + SQL Server + ADLS

App do monorepo espelhando o pipeline [Curso_Pipeline_Azure1](https://github.com/VictorCappelletto/Curso_Pipeline_Azure1) / notebook Databricks `olist_processing.ipynb`.

Ver mapeamento notebook → código: [docs/olist-databricks-mapping.md](../../docs/olist-databricks-mapping.md).

## Fonte de dados (local)

SQL Server Docker → landing CSV → processing parquet → curated CSV.

| Variável | Default |
|----------|---------|
| `MSSQL_SERVER` | `localhost,1433` |
| `MSSQL_DATABASE` | `olist` |
| `MSSQL_USER` | `sa` |
| `MSSQL_SA_PASSWORD` | `Olist@Dev123!` |
| `OLIST_LAKE_BACKEND` | `local` (`adls` para Azure) |
| `OLIST_PROCESSING_ENGINE` | `local` (`spark` para PySpark) |
| `SPARK_MASTER` | `local[*]` ou `spark://localhost:7077` |
| `AZURE_STORAGE_ACCOUNT` | pós-deploy infra |

Ver [docs/spark-processing.md](../../docs/spark-processing.md).

## Estrutura (como Databricks)

```text
ingestion_azure/
├── config/
│   ├── extraction/          # SQL Server + lista de tabelas
│   ├── ingestion/           # domínios legacy
│   ├── transformation/      # tabelas, filtros (customers_RJ)
│   └── consumption/         # bronze/silver/gold → olist_dw
├── extraction/              # pyodbc
├── ingestion/
│   ├── landing_export.py    # SQL → landing CSV (ADF)
│   └── orders.py            # legacy — use olist_demo
├── transformation/          # notebook olist_processing.ipynb
│   ├── base.py              # engine dispatch + notebook steps
│   ├── io.py                # mount + CSV/parquet local/ADLS + Spark paths
│   └── olist.py             # OlistTransformPipeline + SparkSqlCatalog
├── consumption/
│   └── sql_server_publish.py  # landing→bronze, processing→silver, curated→gold
└── tests/
```

```text
ingestion_azure/
├── config/
│   ├── extraction/ ingestion/ transformation/ consumption/
│   ├── orchestration/             # extraction | ingestion | transformation | consumption
│   └── workflows/                 # DAG por processo
├── orchestrator/
│   ├── extraction.py
│   ├── ingestion.py
│   ├── transformation.py
│   └── consumption.py
├── workflows/
│   ├── extraction_dag.py
│   ├── ingestion_dag.py
│   ├── transformation_dag.py
│   ├── consumption_dag.py
│   └── runs/
│       ├── extraction.py
│       ├── ingestion.py
│       ├── transformation.py
│       ├── consumption.py
│       └── olist_demo.py
├── extraction/ ingestion/ transformation/ consumption/
└── tests/
```

## Rodar via workflows (1 runner por processo)

```powershell
set DATA_PLATFORM_APP=ingestion_azure
pip install -e ".[olist]"

python workflows/runs/extraction.py
python workflows/runs/transformation.py --mode from_landing
python workflows/runs/consumption.py
python workflows/runs/ingestion.py          # legacy orders
```

## Pipeline completo (composição)

```powershell
python workflows/runs/olist_demo.py --mode full
python workflows/runs/olist_demo.py --mode transform_from_landing
python workflows/runs/olist_demo.py --mode publish
python workflows/runs/olist_demo.py --mode sql_catalog
```

## Rodar pipeline (domain direto — legado)

**Local (pyarrow):**

```powershell
set DATA_PLATFORM_APP=ingestion_azure
pip install -e ".[olist]"
python -c "from dataplatform.bootstrap import bootstrap; bootstrap('ingestion_azure'); from workflows.runs.olist_demo import run_full; print(run_full())"
```

**Spark (como Databricks):**

```powershell
set OLIST_PROCESSING_ENGINE=spark
set SPARK_MASTER=local[*]
python -c "from dataplatform.bootstrap import bootstrap; bootstrap('ingestion_azure'); from workflows.runs.olist_demo import run_full; print(run_full())"
```

## Roadmap

1. ~~SQL Server local + schema Olist~~
2. ~~App scaffold~~
3. ~~Transformation landing → processing → curated (notebook)~~
4. ~~GitHub Actions / ADF → landing ADLS~~ — [docs/azure-adf-setup.md](../../docs/azure-adf-setup.md)
5. ~~Processing + curated no ADLS~~ — `make azure-olist-transform`
6. ~~Spark SQL catalog (`customers_db`)~~ — `make olist-spark-catalog`
7. ~~Power BI / curated~~ — [docs/power-bi-setup.md](../../docs/power-bi-setup.md) · `make azure-olist-publish-sql` → `olist_dw.gold.*`

Ver também: [docs/sql-server-setup.md](../../docs/sql-server-setup.md), [docs/azure-infra-setup.md](../../docs/azure-infra-setup.md)
