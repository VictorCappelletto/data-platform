# medalion_ingestion_project

Pipeline **medallion local** com dois domínios — prova engenharia de dados pura (sem cloud): ingestão particionada, DQ, transform enriquecido, KPIs e export analítico.

Orquestração: **Airflow** (YAML → DAG) + runners CLI. Storage: lake file local (MinIO/S3 opcional).

---

## Domínios

| Domínio | Fonte | Fluxo | Saída |
|---------|-------|-------|-------|
| **orders** | CSV seed | landing → bronze → silver (SCD) | silver + KPI gold |
| **brewery** | Open Brewery DB / fixture | landing → bronze → silver → gold (particionado) | gold enriquecido |

Volume demo: ~10,5k orders · ~11,8k breweries ([Open Brewery DB](https://www.openbrewerydb.org/), ODbL).

---

## Arquitetura

```text
                    ┌─────────────┐
  orders CSV ──────►│  ingestion  │──► silver ──► KPI transform ──► consumption (export)
                    └─────────────┘

  brewery API/fixture
        │
        ▼
  extraction ──► ingestion (partitioned) ──► transformation (DQ + gold enrich)
```

Layout por **4 processos** (`extraction` · `ingestion` · `transformation` · `consumption`), igual ao app Azure:

```text
config/
├── <processo>/config_<processo>.yml    # domínios e regras
├── orchestration/<processo>.yml        # task → orchestrator → domain module
└── workflows/<processo>.yml            # schedule Airflow

orchestrator/                           # entry points finos (bootstrap + delega)
<processo>/<dominio>.py                 # lógica de negócio
workflows/<processo>_dag.py               # DAG fino (dataplatform.airflow)
workflows/runs/                         # runners locais + medalion_demo.py
```

**Princípios:** config over code · orchestrator fino · contrato documentado em MD (código implementa).

---

## Config relevante

| Arquivo | Conteúdo |
|---------|----------|
| `config/transformation/config_transformation.yml` | KPI metrics, brewery DQ, enrich (`craft_types`, `country_codes`, `us_state_codes`) |
| `config/constants.yml` | KPI baseline, seeds bulk (`seeds.bulk`) |
| `config/extraction/config_extraction.yml` | API Open Brewery (url, paginação, fixture) |
| `config/ingestion/config_ingestion.yml` | paths landing, partition keys brewery |

Contratos: [docs/data-contracts.md](docs/data-contracts.md)

---

## Gold brewery — transform

Silver → gold adiciona colunas derivadas (regras no YAML):

| Coluna | Origem |
|--------|--------|
| `load_date` | partição do pipeline |
| `processed_at` | timestamp UTC do transform |
| `country_code` | mapa `enrich.country_codes` |
| `state_code` | mapa `enrich.us_state_codes` (US) |
| `has_coordinates` | lat/long presentes |
| `is_craft` | `brewery_type` ∈ `enrich.craft_types` |

Implementação: `transformation/brewery.py` · DQ gate: `transformation/base.py` (`run_dq_gold`).

---

## Orquestração

| DAG | Tasks principais |
|-----|------------------|
| `ingestion` | brewery ingest · orders landing/bronze/silver |
| `transformation` | brewery DQ/gold · orders KPI |
| `consumption` | analytics export |
| `extraction` | brewery API/fixture |

Registry: `config/orchestration/*.yml` → `dataplatform.airflow.build_dag_from_yaml`.

---

## Executar

```powershell
set DATA_PLATFORM_APP=medalion_ingestion_project
pip install -e ".[dev]"

# Amostra (CI / dev rápido)
python workflows/runs/medalion_demo.py --mode orders_full
python workflows/runs/medalion_demo.py --mode brewery_full

# Bulk (portfólio)
python workflows/runs/medalion_demo.py --mode orders_full --bulk
python workflows/runs/medalion_demo.py --mode brewery_full --bulk

# Inspecionar lake
python quality/inspect_lake.py
```

Makefile (raiz): `make demo` · `make demo-bulk` · `make brewery-demo-bulk`

Seeds bulk em `config/constants.yml` — flag `--bulk` lê paths de lá.

Regenerar seeds:

```powershell
python seeds/fetch_breweries.py
python seeds/generate_orders.py
```

---

## Testes

```bash
pytest tests -q   # 31 — HDL, brewery, KPI, export, orchestrator, platform
```

Roda isolado (`pytest apps/medalion_ingestion_project/tests`). Não rodar os dois apps juntos no mesmo processo (colisão de imports planos).

---

## Decisões de design

| Decisão | Motivo |
|---------|--------|
| Contrato em MD, não runtime | Acordo documentado; código + DQ já garantem regras |
| Bulk via `--bulk` + YAML | Sem perfil `demo` extra; paths centralizados |
| Particionamento brewery | `country/state/load_date` — exercita layout lake real |
| Sem cloud neste app | Custo zero; Azure fica no `ingestion_azure` |
