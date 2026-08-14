# Data lineage

Lake root (local): `data/lake/local/medalion_ingestion_project/`

## Orders pipeline

```text
apps/medalion_ingestion_project/seeds/orders_raw.csv
        │
        ▼
landing/orders/orders          (raw CSV)
        │
        ▼
bronze/orders/orders           (typed / normalized JSON)
        │
        ▼
silver/orders/orders           (deduped + is_current)
        │
        ▼
gold/kpi/orders_daily          (gmv_completed, active_customers, completion_rate)
        │
        ▼
gold/analytics/kpi_export      (DQ-gated consumption snapshot)
```

DAGs: `hdl_ingest` → `kpi_metrics` → `analytics_export`

## Brewery pipeline

```text
Open Brewery API  (or apps/medalion_ingestion_project/seeds/breweries_sample.json)
        │
        ▼
landing/brewery/breweries/country=*/state=*/load_date=*/
        │
        ▼
bronze/brewery/breweries/...   (typed / normalized)
        │
        ▼
silver/brewery/breweries/...   (deduped by id)
        │
        ▼  DQ (nulls, duplicates, min volume)
gold/brewery/breweries/...     (validated consumption layer)
```

| Step | DAG | Schedule |
|------|-----|----------|
| Ingest | `brewery_ingest` | 06:00 daily |
| DQ + Gold | `brewery_dq_gold` | 07:30 daily |

Both use pool `brewery_pool` and `max_active_runs=1`.

## Olist Azure pipeline (`ingestion_azure`)

Lake root (local): `data/lake/local/ingestion_azure/`  
Lake root (Azure): `abfss://{landing|processing|curated}@{storage}.dfs.core.windows.net/`

```text
SQL Server (Docker, db olist)
        │
        ▼  ADF pl_olist_landing_copy + SHIR
landing/   8 CSVs
        │
        ▼  transformation (local pyarrow or spark)
processing/   8 parquets + customers_RJ.parquet
        │
        ▼  filters (customer_state = RJ)
curated/   customers_RJ.csv
        │
        ├─► Spark SQL customers_db.*_pqt / *_csv  (make olist-spark-catalog)
        └─► SQL Server olist_dw.bronze.* + silver.* + gold.*  (make azure-olist-publish-sql)
                │
                ▼
            Power BI Desktop
```

Commands: `make azure-adf-trigger` → `make azure-olist-transform` → `make azure-olist-publish-sql`

See [power-bi-setup.md](./power-bi-setup.md), [olist-databricks-mapping.md](./olist-databricks-mapping.md).
