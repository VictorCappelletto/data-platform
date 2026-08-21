# ingestion_azure

Pipeline **Olist** em **Azure SQL + ADF + ADLS** — landing via Copy; **transform + publish via Python Custom Activity** (Azure Batch + ACR).

Referência: [Curso_Pipeline_Azure1](https://github.com/VictorCappelletto/Curso_Pipeline_Azure1) · [olist-databricks-mapping.md](../../docs/olist-databricks-mapping.md)

---

## Fluxo (ADF master pipeline)

```text
pl_olist_end_to_end
├── pl_olist_landing_copy     Azure SQL olist → ADLS landing/*.csv        (Copy)
├── pl_olist_transform        landing → processing + curated              (Custom Activity / Python)
└── pl_olist_publish_sql      ADLS → Azure SQL olist_dw bronze/silver/gold (Custom Activity / Python)
                                      └── Power BI Desktop
```

Cloud-to-cloud — **sem Self-hosted IR** no caminho principal.

| Etapa | Activity ADF | Detalhe |
|-------|--------------|---------|
| Landing | ForEach + Copy | `AzureSqlSource` → DelimitedText (8 tabelas) |
| Transform | Custom Activity | Container `olist-transform` — CSV→Parquet + `customers_RJ` |
| Publish | Custom Activity | Container — `olist_demo.py --mode publish` → `olist_dw` |

Artefatos: `infra/adf/pipelines/` · Compute: ACR + Azure Batch (`infra/modules/acr.bicep`, `batch.bicep`)

---

## Infra (Bicep)

| Recurso | Módulo |
|---------|--------|
| ADLS Gen2 (landing, processing, curated) | `infra/modules/storage.bicep` |
| Data Factory + MI → storage RBAC | `infra/modules/datafactory.bicep` |
| Azure SQL (olist + olist_dw, Basic tier) | `infra/modules/sql.bicep` |
| ACR (imagem Python) | `infra/modules/acr.bicep` |
| Azure Batch + pool container | `infra/modules/batch.bicep` |

---

## Deploy e execução

```powershell
# 1. Secrets + infra
make env-prepare
make azure-infra-deploy          # AZURE_SQL_ADMIN_PASSWORD from SOPS → .env

# 2. Seed Azure SQL (schema + dados Olist)
make azure-sql-seed

# 3. Build/push imagem + publicar ADF
make azure-adf-deploy            # push-transform-image + publish-adf

# 4. Pipeline completo (1 clique)
make azure-olist-full
```

Somente landing: `make azure-adf-trigger`

---

## Variáveis (.env pós-deploy)

| Variável | Descrição |
|----------|-----------|
| `AZURE_SQL_SERVER` | FQDN (`*.database.windows.net`) |
| `AZURE_SQL_ADMIN_LOGIN` | default `olistadmin` |
| `AZURE_SQL_ADMIN_PASSWORD` | **SOPS** (`make secrets-set`) — fallback `MSSQL_SA_PASSWORD` |
| `AZURE_STORAGE_ACCOUNT` | ADLS |
| `AZURE_DATA_FACTORY_NAME` | ADF |
| `AZURE_ACR_LOGIN_SERVER` | Registry da imagem transform |
| `AZURE_BATCH_ACCOUNT_NAME` | Batch para Custom Activity |
| `AZURE_TRANSFORM_IMAGE` | ex. `myacr.azurecr.io/olist-transform:latest` |

Preenchidas por `docker/azure/sync-deploy-outputs.ps1`.

---

## Local (dev offline — legado)

Python runners + SQL Docker continuam disponíveis para dev sem Azure:

```powershell
set DATA_PLATFORM_APP=ingestion_azure
pip install -e ".[olist]"
make sql-init
python workflows/runs/olist_demo.py --mode full
```

Scripts Makefile `azure-olist-transform` / `azure-olist-publish-sql` = mesmo código Python, execução local (sem Batch).

---

## Testes

```bash
pytest apps/ingestion_azure/tests -q   # 17
```

Testam lógica Python (local/spark). Pipelines ADF validados via run no portal / `make azure-olist-full`.

---

## Docs

| Doc | Conteúdo |
|-----|----------|
| [azure-infra-setup.md](../../docs/azure-infra-setup.md) | Bicep deploy |
| [azure-adf-setup.md](../../docs/azure-adf-setup.md) | ADF publish + pipelines |
| [power-bi-setup.md](../../docs/power-bi-setup.md) | Consumo `olist_dw.gold.*` |

---

## Decisões

| Decisão | Motivo |
|---------|--------|
| Azure SQL vs Docker+SHIR | Cloud-to-cloud, sem IR local, portfolio sênior |
| Custom Activity vs Copy transform | Mesmo código Python dos testes; filtros/curated no lake |
| Landing ainda Copy | Bulk SQL→ADLS é caso ideal para Copy nativo |
| Python local mantido | Testes unitários + dev offline |
