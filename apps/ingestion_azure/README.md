# ingestion_azure



Pipeline **Olist** em **Azure SQL + ADF + ADLS** — 100% orquestrado no ADF com **Copy nativo** (sem Batch, sem container, sem SHIR no caminho crítico).



Referência: [Curso_Pipeline_Azure1](https://github.com/VictorCappelletto/Curso_Pipeline_Azure1) · [olist-databricks-mapping.md](../../docs/olist-databricks-mapping.md)



---



## Fluxo (ADF master pipeline)



```text

pl_olist_end_to_end

├── pl_olist_landing_copy     Azure SQL olist → ADLS landing/*.csv

├── pl_olist_transform        landing CSV → processing/*.parquet + curated/customers_RJ.csv

└── pl_olist_publish_sql      ADLS → Azure SQL olist_dw (bronze / silver / gold)

                                      └── Power BI Desktop

```



Cloud-to-cloud — **sem Self-hosted IR** no caminho principal.



| Etapa | Activity ADF | Detalhe |

|-------|--------------|---------|

| Landing | ForEach + Copy | `AzureSqlSource` → DelimitedText (8 tabelas) |

| Transform | ForEach + Copy | CSV → Parquet (8 tabelas) |

| Curated | Copy | SQL query `customer_state = 'RJ'` → `curated/customers_RJ.csv` |

| Publish bronze | ForEach + Copy | landing CSV → `olist_dw.bronze.*` |

| Publish silver | ForEach + Copy | processing parquet → `olist_dw.silver.*` |

| Publish gold | ForEach + Copy | curated CSV → `olist_dw.gold.*` |



Artefatos: `infra/adf/pipelines/` · Linked services: `ls_azure_sql_olist`, `ls_azure_sql_dw`, `ls_adls_olist`



---



## Infra (Bicep)



| Recurso | Módulo |

|---------|--------|

| ADLS Gen2 (landing, processing, curated) | `infra/modules/storage.bicep` |

| Data Factory + MI → storage RBAC | `infra/modules/datafactory.bicep` |

| Azure SQL (olist + olist_dw, Basic tier) | `infra/modules/sql.bicep` |



Deploy via **portal Cloud Shell** se `az login` local estiver bloqueado (Security Defaults) — ver [azure-cloudshell-deploy.md](../../docs/azure-cloudshell-deploy.md).



---



## Deploy e execução



```powershell

# 1. Secrets + infra

make env-prepare

make azure-infra-deploy          # ou Cloud Shell / GitHub Actions azure-infra



# 2. Seed Azure SQL

make azure-sql-seed



# 3. Publicar ADF

make azure-adf-publish



# 4. Pipeline completo

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



Scripts `azure-olist-transform` / `azure-olist-publish-sql` = mesmo código Python, execução local.



---



## Testes



```bash

pytest apps/ingestion_azure/tests -q

```



---



## Docs



| Doc | Conteúdo |

|-----|----------|

| [azure-infra-setup.md](../../docs/azure-infra-setup.md) | Bicep deploy |

| [azure-adf-setup.md](../../docs/azure-adf-setup.md) | ADF publish + pipelines |

| [azure-cloudshell-deploy.md](../../docs/azure-cloudshell-deploy.md) | Deploy via Cloud Shell (Win10 / 530035) |

| [secrets-pipeline.md](../../docs/secrets-pipeline.md) | SOPS / senhas |



---



## Decisões



| Decisão | Motivo |

|---------|--------|

| Copy nativo vs Custom Activity | Zero compute extra; sem Docker/Batch; funciona só com portal + ADF |

| `customers_RJ` via SQL query | Copy não filtra CSV; query na source é Copy-native |

| Python local mantido | Testes unitários + dev offline |

