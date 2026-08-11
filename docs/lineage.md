# Data lineage (demo)

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

## KPI definitions (synthetic)

| KPI | Rule |
|-----|------|
| `gmv_completed` | Sum of `amount` where `status=completed` and `is_current` |
| `active_customers` | Distinct `customer_id` on current rows |
| `completion_rate` | completed / current |
