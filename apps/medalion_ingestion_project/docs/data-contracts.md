# Contratos de dados — medalion_ingestion_project

Documentação do acordo entre **produtor** (pipelines) e **consumidor** (KPI, export, inspect).  
O código implementa estas regras; não há validador separado — o contrato é a especificação.

**Owner:** Victor Cappelletto  
**Contato:** https://github.com/VictorCappelletto  
**Freshness:** batch diário — dados de D-1 disponíveis até **08:00 America/Sao_Paulo**

---

## orders.silver.orders

Pedidos limpos, com histórico SCD (`is_current`).

| Coluna | Tipo | Obrigatório | Regra |
|--------|------|-------------|-------|
| `order_id` | string | sim | único por versão corrente |
| `customer_id` | string | sim | |
| `amount` | number | sim | > 0 |
| `status` | string | sim | `completed`, `pending`, `cancelled` (lowercase) |
| `country` | string | sim | ISO-like uppercase (default `BR`) |
| `event_ts` | string | sim | ISO-8601 UTC |
| `load_at` | string | sim | data de carga `YYYY-MM-DD` |
| `is_current` | boolean | sim | uma linha corrente por `order_id` |

**Volume demo:** ~10k linhas (`seeds/orders_bulk.csv`)  
**Implementação:** `ingestion/orders.py`

---

## kpi.gold.orders_daily

Métricas agregadas derivadas de orders silver (apenas `is_current=true`).

| Coluna | Tipo | Obrigatório | Regra |
|--------|------|-------------|-------|
| `kpi_name` | string | sim | `gmv_completed`, `active_customers`, `completion_rate` |
| `kpi_value` | number | sim | |
| `country` | string | sim | default `BR` |
| `grain` | string | sim | `daily` |

**Volume:** exatamente 3 linhas por execução  
**Implementação:** `transformation/kpi.py`

---

## brewery.gold.breweries

Dimensão enriquecida, particionada por `country/state/load_date`.

| Coluna | Tipo | Obrigatório | Regra |
|--------|------|-------------|-------|
| `id`, `name`, `brewery_type` | string | sim | não nulos (DQ gate) |
| `load_date` | string | sim | partição |
| `processed_at` | string | sim | UTC ISO-8601 |
| `country_code` | string | sim | mapa `enrich.country_codes` no YAML |
| `state_code` | string | não | mapa `enrich.us_state_codes` (US) |
| `has_coordinates` | boolean | sim | lat/long válidos |
| `is_craft` | boolean | sim | `brewery_type` ∈ `enrich.craft_types` |

**Volume demo:** ~11k linhas (`seeds/breweries_bulk.json`, [Open Brewery DB](https://www.openbrewerydb.org/), ODbL)  
**Implementação:** `transformation/brewery.py` + DQ em `transformation/base.py`

---

## Seeds bulk (regenerar)

```powershell
python apps/medalion_ingestion_project/seeds/fetch_breweries.py
python apps/medalion_ingestion_project/seeds/generate_orders.py
```

Demo com volume alto:

```powershell
make demo-bulk
make brewery-demo-bulk
```
