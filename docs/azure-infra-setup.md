# Azure infra — portfolio Olist (custo mínimo)

Estratégia: **só paga quando usa**. Resource Group é gratuito; serviços caros (ADF, Databricks, Synapse) ficam para fases posteriores.

## Fase 3 — Storage ADLS Gen2 ✅

Implementado em `infra/modules/storage.bicep` — deploy via `infra/main.bicep` (local ou GitHub Actions).

| Recurso | Config | Custo |
|---------|--------|-------|
| Storage Account | Standard_LRS, Hot, HNS enabled | ~US$ 0,02/GB/mês |
| Containers | `landing`, `processing`, `curated` | incluso |
| Shared key | **desabilitado** | — |
| Acesso | RBAC (OIDC / `az login`) | — |

### Deploy local

```powershell
az deployment sub what-if -l eastus -f infra/main.bicep -p infra/parameters/dev.bicepparam
az deployment sub create -l eastus -f infra/main.bicep -p infra/parameters/dev.bicepparam --name "local-storage"
powershell -ExecutionPolicy Bypass -File docker/azure/sync-deploy-outputs.ps1
powershell -ExecutionPolicy Bypass -File docker/azure/verify-storage.ps1
```

Ou via GitHub Actions: push em `infra/**` dispara [azure-infra.yml](../.github/workflows/azure-infra.yml).

### Variáveis pós-deploy (`.env`)

| Variável | Secret? | Origem |
|----------|---------|--------|
| `AZURE_STORAGE_ACCOUNT` | Não | output do deploy |
| `AZURE_ADLS_ENDPOINT` | Não | output do deploy (`*.dfs.core.windows.net`) |

### Verificar

```powershell
powershell -ExecutionPolicy Bypass -File docker/azure/verify-storage.ps1
az storage container list --account-name <nome> --auth-mode login -o table
```

## Estado atual

| Recurso | Nome | Região | Custo |
|---------|------|--------|-------|
| Resource Group | `rg-olist-dev` | `eastus` | **Grátis** |
| Storage ADLS Gen2 | `stolist*` (auto, pós-deploy) | `eastus` | **~US$ 0,02/GB/mês** |

Subscription: `82700697-643d-4ea8-aebe-57c85a333594`  
Tenant: `3950d3d0-769c-4153-a41d-c02adbfe1f35`

## Fases (ordem recomendada)

| Fase | O quê | Custo estimado |
|------|-------|----------------|
| **1** ✅ | Resource Group | Grátis |
| **2** ✅ | GitHub → Azure (OIDC, sem secret) | Grátis |
| **3** ✅ | Storage ADLS Gen2 (LRS, mínimo) | ~US$ 0,02/GB/mês |
| **4** ✅ | Azure Data Factory (só quando rodar pipeline) | ~US$ 1/milhão execuções |
| **5** ✅ | Self-hosted IR (SQL local) | IR local = grátis |

**Não criar agora:** Databricks, Synapse, Azure SQL (serverless) — só quando o portfolio precisar.

## IaC (Bicep)

```powershell
# Validar
az deployment sub what-if -l eastus -f infra/main.bicep -p infra/parameters/dev.bicepparam

# Aplicar (idempotente)
az deployment sub create -l eastus -f infra/main.bicep -p infra/parameters/dev.bicepparam --name "local-$(Get-Date -Format yyyyMMddHHmmss)"
```

## Fase 2 — GitHub Actions OIDC (Docker Compose)

Sem `client_secret` — o workflow usa OpenID Connect com 3 secrets no GitHub.

### Passo A — Criar App Registration + federated credential (uma vez)

Requer `az login` no host.

**Windows (recomendado):**

```powershell
docker compose --profile secrets run --rm secrets prepare
powershell -ExecutionPolicy Bypass -File docker/azure/setup-oidc.ps1
```

Cria credenciais federadas para **`main`** e **`publish-main`**.

**Linux / CI local (Docker):**

```powershell
docker compose --profile azure build azure
docker compose --profile azure run --rm azure setup
```

> No Windows, o mount de `%USERPROFILE%\.azure` no container pode falhar — use o script PowerShell acima.

Saída: `config/azure/oidc.generated.env` (gitignored) com `AZURE_CLIENT_ID`, etc.

### Passo B — Secrets no GitHub

**Opção 1 — automático** (requer `gh auth login`):

```powershell
powershell -ExecutionPolicy Bypass -File docker/azure/push-github-secrets.ps1
```

**Opção 2 — manual** — Settings → Secrets and variables → Actions:

| Secret | Origem |
|--------|--------|
| `AZURE_CLIENT_ID` | `oidc.generated.env` |
| `AZURE_TENANT_ID` | `3950d3d0-769c-4153-a41d-c02adbfe1f35` |
| `AZURE_SUBSCRIPTION_ID` | `82700697-643d-4ea8-aebe-57c85a333594` |

**Não precisa** de `AZURE_CLIENT_SECRET`.

### Passo C — Workflow

[`.github/workflows/azure-infra.yml`](../.github/workflows/azure-infra.yml) roda em:

- push para `main`/`master` com mudanças em `infra/**`
- `workflow_dispatch` manual

Dispara: login OIDC → verify RG → what-if → deploy Bicep.

### Verificar localmente

```powershell
docker compose --profile azure run --rm --entrypoint verify-oidc azure
powershell -ExecutionPolicy Bypass -File docker/azure/verify-rg.ps1
```

### Detalhes técnicos

| Item | Valor |
|------|-------|
| App Registration | `sp-data-platform-github` |
| Federated subjects | `main` + `publish-main` |
| RBAC | Contributor em `rg-olist-dev` apenas |

## Fase 3 — Storage (legado — ver seção acima)

Conteúdo movido para **Fase 3 — Storage ADLS Gen2** no topo deste documento.

## Fase 4 — Azure Data Factory ✅

Implementado em `infra/modules/datafactory.bicep` + artefatos em `infra/adf/`.

| Recurso | Config |
|---------|--------|
| Data Factory | Nome auto `adf-olist*` + system-assigned MI |
| RBAC | MI → Storage Blob Data Contributor |
| Pipeline | `pl_olist_landing_copy` — 8 tabelas → `landing/*.csv` |
| IR | Self-hosted `shir-olist-dev` (registro = Fase 5) |

Guia completo: [azure-adf-setup.md](./azure-adf-setup.md)

```powershell
make azure-infra-deploy          # inclui factory
make azure-adf-publish           # linked services + pipeline
make azure-verify-adf
make azure-shir-setup            # Fase 5 — SQL local
make azure-adf-trigger           # executar copy
```

## SQL local + ADF

O SQL Server Docker (`localhost:1433`) não é acessível pelo ADF na nuvem. Opções:

1. **Self-hosted Integration Runtime** na sua máquina (grátis, bom para portfolio)
2. Pipeline Python local (`ingestion_azure`) enquanto IR não existir
3. Azure SQL (pago) — só se quiser 100% cloud

## Comandos úteis

```powershell
az group show -n rg-olist-dev
az deployment sub list --query "[?contains(name,'main')]" -o table
az role assignment list --scope "/subscriptions/82700697-643d-4ea8-aebe-57c85a333594/resourceGroups/rg-olist-dev" -o table
```

## Referências

- [Azure ADF setup (Fase 4)](./azure-adf-setup.md)
- [Azure MCP setup](./azure-mcp-setup.md)
- [SQL Server local](./sql-server-setup.md)
- [GitHub OIDC with Azure](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure)
