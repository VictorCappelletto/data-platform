# Azure Data Factory — Olist pipeline (Azure SQL + Copy)

ADF orquestra **100% cloud**: Azure SQL → ADLS → transform (Copy) → Azure SQL `olist_dw`.

## Pipelines

| Pipeline | Função |
|----------|--------|
| `pl_olist_landing_copy` | 8 tabelas `olist` → ADLS `landing/*.csv` |
| `pl_olist_transform` | CSV → `processing/*.parquet` + `curated/customers_RJ.csv` |
| `pl_olist_publish_sql` | ADLS → `olist_dw` bronze/silver/gold |
| `pl_olist_end_to_end` | Master — encadeia os 3 acima |

## Pré-requisitos

- Infra deployada (`make azure-infra-deploy` ou Cloud Shell / GitHub Actions)
- Dados seed (`make azure-sql-seed`)
- `.env` com outputs (`sync-deploy-outputs.ps1`)

> **Windows + Security Defaults:** se `az login` local falhar (530035), use [azure-cloudshell-deploy.md](azure-cloudshell-deploy.md).

## Publicar

```powershell
make env-prepare
make azure-adf-publish
```

Substitui placeholders: `__ADLS_URL__`, `__AZURE_SQL_OLIST_CONNECTION__`, `__AZURE_SQL_DW_CONNECTION__`  
Senha SQL via SOPS — ver [secrets-pipeline.md](secrets-pipeline.md).

## Executar

```powershell
make azure-olist-full
make azure-adf-trigger         # só landing
```

Portal: [adf.azure.com](https://adf.azure.com) → `pl_olist_end_to_end` → Trigger

## Linked services

| Nome | Tipo | Uso |
|------|------|-----|
| `ls_adls_olist` | AzureBlobFS | ADLS Gen2 (MI auth) |
| `ls_azure_sql_olist` | AzureSqlDatabase | Source `olist` |
| `ls_azure_sql_dw` | AzureSqlDatabase | Consumo `olist_dw` |

**Sem SHIR** no fluxo principal. SHIR permanece no repo apenas para dev local legado.

## Limitação Copy nativo

Copy não filtra CSV in-place — `customers_RJ` usa **Copy com SQL query** na source Azure SQL.

Detalhes infra: [azure-infra-setup.md](azure-infra-setup.md)
