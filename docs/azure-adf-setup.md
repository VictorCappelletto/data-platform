# Azure Data Factory — Olist pipeline (Custom Activity + Copy)

ADF orquestra **cloud-to-cloud**: Azure SQL → ADLS (Copy) → transform/publish (Python Custom Activity on Batch).

## Pipelines

| Pipeline | Função |
|----------|--------|
| `pl_olist_landing_copy` | 8 tabelas `olist` → ADLS `landing/*.csv` (Copy) |
| `pl_olist_transform` | Python: landing → `processing/*.parquet` + `curated/customers_RJ.csv` |
| `pl_olist_publish_sql` | Python: ADLS → `olist_dw` bronze/silver/gold |
| `pl_olist_end_to_end` | Master — encadeia os 3 acima |

## Pré-requisitos

- Infra deployada (`make azure-infra-deploy`) — SQL + ACR + Batch
- Dados seed (`make azure-sql-seed`)
- Docker local (build/push imagem)
- `az login`
- `.env` com outputs (`sync-deploy-outputs.ps1`)

## Publicar

```powershell
make env-prepare                    # decrypt secrets → .env
make azure-transform-image-push     # build + push olist-transform:latest
make azure-adf-publish              # linked services + pipelines
# ou tudo junto:
make azure-adf-deploy
```

Substitui placeholders: ADLS, SQL connections, Batch/ACR credentials, imagem container.  
Senha SQL via SOPS — ver [secrets-pipeline.md](secrets-pipeline.md).

## Executar

```powershell
make azure-olist-full          # master pipeline
make azure-adf-trigger         # só landing
```

Portal: [adf.azure.com](https://adf.azure.com) → `pl_olist_end_to_end` → Trigger

## Linked services

| Nome | Tipo | Uso |
|------|------|-----|
| `ls_adls_olist` | AzureBlobFS | ADLS Gen2 (MI auth) |
| `ls_azure_sql_olist` | AzureSqlDatabase | Source `olist` |
| `ls_azure_sql_dw` | AzureSqlDatabase | Consumo `olist_dw` |
| `ls_azure_batch` | AzureBatch | Custom Activity compute |
| `ls_acr_olist` | AzureContainerRegistry | Imagem Python |
| `ls_batch_staging_storage` | AzureBlobStorage | Staging ADF/Batch |

**Sem SHIR** no fluxo principal.

## Imagem container

Dockerfile: `docker/ingestion_azure/Dockerfile`  
Entrypoint: `python workflows/runs/olist_demo.py --mode transform_from_landing|publish`

Pool Batch (`olist-pool`) usa managed identity para ADLS + ACR pull.

## Artefatos

```text
infra/adf/
├── linkedservices/
├── datasets/
└── pipelines/
```

Detalhes infra: [azure-infra-setup.md](azure-infra-setup.md)
