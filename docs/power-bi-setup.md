# Power BI — curated consumption (Olist / ingestion_azure)

Connect Power BI Desktop to the **curated** layer after the medallion pipeline completes.

## End-to-end flow

```text
SQL Server (olist) ──ADF+SHIR──► ADLS landing/
                                      │
                               azure-olist-transform
                                      │
                               processing/ + curated/
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
         Spark customers_db                    SQL Server olist_dw
    (Databricks notebook port)              bronze.* + silver.* + gold.* (Power BI)
                    │                                   │
                    └──────────── Power BI ─────────────┘
```

## Option A — SQL Server (recommended for portfolio)

No Databricks workspace cost. Lake zones map to SQL schemas:

| Lake zone | SQL schema | Exemplo |
|-----------|------------|---------|
| `landing/` | `bronze.*` | `olist_dw.bronze.customers` |
| `processing/` | `silver.*` | `olist_dw.silver.orders` |
| `curated/` | `gold.*` | `olist_dw.gold.customers_RJ` |

### 1. Ensure SQL Server + lake data exist

```powershell
make sql-init                    # olist (source) + olist_dw (bronze/silver/gold schemas)
make azure-adf-trigger           # landing on ADLS (if using Azure)
make azure-olist-transform       # processing + curated on ADLS
make azure-olist-publish-sql     # bronze.* + silver.* + gold.* in olist_dw
```

Local lake only:

```powershell
# run pipeline locally first, then:
powershell -File docker/consumption/publish-curated-sql.ps1
```

### 2. Power BI Desktop — SQL Server

1. **Get data** → **SQL Server**
2. Server: `localhost,1433`
3. Database: `olist_dw`
4. Data connectivity mode: **Import**
5. Select **`gold.customers_RJ`** (60 rows, `customer_state = RJ`)
6. Optional: join with **`silver.customers`**, **`bronze.orders`**, etc.

Credentials:

| Field | Value |
|-------|-------|
| User | `sa` |
| Password | `Olist@Dev123!` (or `MSSQL_SA_PASSWORD`) |

### 3. Sample visuals

- **Card**: total customers (distinct `customer_id`)
- **Map** or **Filled map**: `customer_city` by count
- **Table**: `customer_id`, `customer_city`, `customer_state`

Refresh after re-running `make azure-olist-publish-sql`.

---

## Option B — ADLS Gen2 (direct CSV)

Skip SQL Server; read `curated/customers_RJ.csv` from storage.

1. **Get data** → **Azure** → **Azure Data Lake Storage Gen2**
2. Account: `stolistb3mellxazzrma` (or your `AZURE_STORAGE_ACCOUNT`)
3. Navigate: `curated` → `customers_RJ.csv`
4. Sign in with the same Azure account that has **Storage Blob Data Contributor**

M query (Advanced editor):

```powerquery
let
    Source = Csv.Document(
        Web.Contents(
            "https://stolistb3mellxazzrma.dfs.core.windows.net/curated/customers_RJ.csv"
        ),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    Promoted
```

For production, prefer **Azure AD** + connector UI instead of anonymous `Web.Contents`.

---

## Option C — Spark SQL catalog (Databricks equivalent)

Registers external tables in Spark catalog `customers_db` (notebook cells 19–73):

| Spark table | Lake path |
|-------------|-----------|
| `customers_db.customers_pqt` | `processing/customers.parquet` |
| `customers_db.customers_RJ_pqt` | `processing/customers_RJ.parquet` |
| `customers_db.customers_RJ_csv` | `curated/customers_RJ.csv` |

```powershell
# Local lake (requires Java + pyspark)
set OLIST_PROCESSING_ENGINE=spark
set SPARK_MASTER=local[*]
make olist-spark-catalog
```

Query in PySpark:

```python
from runtime import bootstrap
bootstrap()
from transformation.olist import run_sql_catalog
run_sql_catalog()

from dataplatform.lake import get_spark
spark = get_spark("ingestion_azure-customers_db")
spark.table("customers_db.customers_RJ_csv").show()
```

### Power BI + Databricks (when workspace exists)

1. Deploy Databricks workspace + mount ADLS (or use Unity Catalog external locations)
2. Run equivalent `%sql` DDL from [olist-databricks-mapping.md](./olist-databricks-mapping.md)
3. Power BI: **Get data** → **Azure Databricks** → SQL warehouse → `customers_db.customers_RJ_csv`

---

## Makefile targets

| Target | Makefile | Description |
|--------|----------|-------------|
| `make olist-spark-catalog` | Spark SQL `customers_db` over local/adls paths |
| `make azure-olist-publish-sql` | ADLS → `olist_dw.bronze.*` + `silver.*` + `gold.*` |
| `make olist-publish-sql` | Local lake → `olist_dw.bronze.*` + `silver.*` + `gold.*` |

## Related docs

- [olist-databricks-mapping.md](./olist-databricks-mapping.md)
- [spark-processing.md](./spark-processing.md)
- [azure-adf-setup.md](./azure-adf-setup.md)
