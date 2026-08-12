# Data lineage

## Generic demo (orders)

```text
seeds/orders_raw.csv
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

## Brewery ETL (Desafio_InBev adapted)

```text
Open Brewery API  (or seeds/breweries_sample.json)
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
        ▼  platform_dq (nulls, duplicates, min volume)
gold/brewery/breweries/...     (validated consumption layer)
```

### Airflow orchestration

| Step | DAG | Schedule |
|------|-----|----------|
| Ingest | `brewery_ingest` | 06:00 daily |
| DQ + Gold | `brewery_dq_gold` | 07:30 daily |

Both use pool `brewery_pool` (1 slot) and `max_active_runs=1`.
