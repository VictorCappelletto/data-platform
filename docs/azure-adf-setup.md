# Azure Data Factory — Phase 4 (Olist landing)

ADF orquestra **SQL Server → ADLS landing** (8 CSVs), equivalente a `landing_export.py`. Processing/curated continuam em Python/Spark.

## Arquitetura

```text
SQL Server (dbo.*)  --[Copy, SHIR]-->  abfss://landing/{table}.csv
                                              |
                                              v
                                    Python/Spark (processing/curated)
```

| Artefato ADF | Arquivo | Função |
|--------------|---------|--------|
| Self-hosted IR | `infra/adf/integrationruntimes/shir_olist_dev.json` | Acesso ao SQL Docker local |
| Linked service ADLS | `infra/adf/linkedservices/ls_adls_olist.json` | MI auth → storage account |
| Linked service SQL | `infra/adf/linkedservices/ls_sql_olist.json` | `localhost,1433` via SHIR |
| Pipeline | `infra/adf/pipelines/pl_olist_landing_copy.json` | ForEach 8 tabelas → CSV |

## Pré-requisitos

- Fases 1–3 concluídas (RG, OIDC, ADLS Gen2)
- `az login` ativo
- SQL Server Docker rodando (`docker compose up -d sqlserver`)
- `.env` com `MSSQL_SA_PASSWORD` (via `make env-prepare`)

## Passo 1 — Deploy factory (Bicep)

Incluído em `infra/main.bicep` → módulo `datafactory.bicep`:

- Factory com **system-assigned managed identity**
- RBAC **Storage Blob Data Contributor** no storage account

```powershell
az deployment sub what-if -l eastus -f infra/main.bicep -p infra/parameters/dev.bicepparam
az deployment sub create -l eastus -f infra/main.bicep -p infra/parameters/dev.bicepparam --name "local-adf"
powershell -ExecutionPolicy Bypass -File docker/azure/sync-deploy-outputs.ps1
```

Ou: `make azure-infra-deploy`

Variáveis adicionadas ao `.env`:

| Variável | Origem |
|----------|--------|
| `AZURE_DATA_FACTORY_NAME` | output Bicep |

## Passo 2 — Publicar pipelines

Substitui placeholders (`__ADLS_URL__`, `__SQL_CONNECTION_STRING__`) e publica IR, linked services, datasets e pipeline:

```powershell
make azure-adf-publish
# ou
powershell -ExecutionPolicy Bypass -File docker/azure/publish-adf.ps1
```

## Passo 3 — Verificar

```powershell
make azure-verify-adf
```

## Passo 4 — Self-hosted IR (Phase 5)

O ADF na nuvem não alcança `localhost:1433`. Registre o Integration Runtime na sua máquina:

```powershell
# Instala (winget) + registra node (admin/UAC)
make azure-shir-setup

# Se ficar Offline, repare como Administrador:
powershell -ExecutionPolicy Bypass -File docker/azure/repair-shir-admin.ps1
```

Requisitos:
- SQL Docker rodando (`docker compose up -d sqlserver`)
- .NET Framework 4.7.2+
- Outbound HTTPS (443) para Azure Service Bus
- IR com state **Online** (`verify-adf.ps1`)

Instalação: `winget install Microsoft.IntegrationRuntime` (substitui link quebrado `linkid=882275`).

## Passo 6 — Processing + curated (ADLS)

Após o ADF popular `landing/`, rode transformation Python direto no ADLS:

```powershell
make azure-olist-transform
```

Requisitos:
- `az login` com **Storage Blob Data Contributor** no storage account
- `pip install azure-identity azure-storage-file-datalake` (incluído em `[olist]`)

Saída:
- `processing/*.parquet` — 8 tabelas
- `processing/customers_RJ.parquet` — filtro RJ
- `curated/customers_RJ.csv` — 60 linhas

## Passo 5 — Executar landing copy

**Local:**

```powershell
make azure-adf-trigger
```

**GitHub Actions:** Actions → `azure-adf-landing` → Run workflow

**Portal:** [adf.azure.com](https://adf.azure.com) → `pl_olist_landing_copy` → Trigger → Debug

Saída esperada em ADLS:

```text
landing/customers.csv
landing/orders.csv
... (8 arquivos)
```

Verificar:

```powershell
az storage blob list --account-name $env:AZURE_STORAGE_ACCOUNT --container-name landing --auth-mode login -o table
```

## Tabelas (espelham config_extraction.yml)

`customers`, `geolocation`, `order_items`, `order_payments`, `order_reviews`, `orders`, `sellers`, `product_category_name_translation`

## Custo

~US$ 1/milhão de execuções de atividade. Factory parada = sem cobrança de pipeline. SHIR local = grátis.

## Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| SHIR Offline / serviceBus False | Relógio Windows dessincronizado (`AuthSasEffectiveInFuture`) | `fix-shir-clock-admin.ps1` ou `w32tm /resync /force` |
| Copy failed — cannot connect SQL | SHIR não registrado | `setup-shir.ps1` |
| Authorization failed ADLS | MI sem RBAC | redeploy Bicep (role assignment) |
| Pipeline not found | Artefatos não publicados | `publish-adf.ps1` |
| SHIR Offline | Gateway parado | Abrir Integration Runtime Configuration Manager |

## Referências

- [azure-infra-setup.md](./azure-infra-setup.md) — fases 1–5
- [sql-server-setup.md](./sql-server-setup.md)
- [olist-databricks-mapping.md](./olist-databricks-mapping.md)
- [Curso_Pipeline_Azure1](https://github.com/VictorCappelletto/Curso_Pipeline_Azure1)
