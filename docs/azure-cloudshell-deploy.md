# Deploy Olist via Azure Cloud Shell

Guia para deploy **sem `az login` local** — ideal quando Security Defaults bloqueia o Azure CLI no Windows 10 (erro **530035**).

O Cloud Shell usa autenticação do browser no portal; **Copy nativo ADF** — sem Docker, Batch ou container.

## Pré-requisitos

- Subscription: `82700697-643d-4ea8-aebe-57c85a333594`
- Resource group: `rg-olist-dev` (criado pelo Bicep se não existir)
- Senha forte para Azure SQL (ex.: a mesma do portfolio dev — **não commitar**)

## Opção A — Script único (recomendado)

1. Abra [portal.azure.com](https://portal.azure.com) → ícone **`>_`** → **Bash**
2. Cole:

```bash
export AZURE_SQL_ADMIN_PASSWORD='SUA_SENHA_FORTE_AQUI'

git clone --branch publish-main --depth 1 https://github.com/VictorCappelletto/data-platform.git ~/data-platform
cd ~/data-platform
bash docker/azure/cloudshell-deploy.sh
```

O script executa em ordem:

| Etapa | O quê |
|-------|--------|
| 1 | Bicep — ADLS + ADF + Azure SQL |
| 2 | Seed SQL (`docker/sql/init/*.sql`) |
| 3 | Publish ADF (`publish-adf.ps1`) |
| 4 | Trigger `pl_olist_end_to_end` |

### Pular etapas (re-deploy)

```bash
cd ~/data-platform
export AZURE_SQL_ADMIN_PASSWORD='...'
SKIP_INFRA=1 bash docker/azure/cloudshell-deploy.sh          # só seed + publish + pipeline
SKIP_INFRA=1 SKIP_SEED=1 bash docker/azure/cloudshell-deploy.sh   # só publish + pipeline
```

---

## Opção B — Passo a passo manual

### 1. Cloud Shell + clone

```bash
git clone --branch publish-main --depth 1 https://github.com/VictorCappelletto/data-platform.git ~/data-platform
cd ~/data-platform
az account show -o table
```

### 2. Deploy infra (Bicep)

```bash
export SQL_PASS='SUA_SENHA_FORTE_AQUI'
DEPLOY_NAME="cloudshell-$(date +%Y%m%d%H%M%S)"

az deployment sub what-if \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam "sqlAdminPassword=$SQL_PASS"

az deployment sub create \
  --location eastus \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam "sqlAdminPassword=$SQL_PASS" \
  --name "$DEPLOY_NAME"
```

### 3. Gerar `.env` local no Cloud Shell

```bash
az deployment sub show --name "$DEPLOY_NAME" --query properties.outputs -o json > /tmp/out.json

python3 <<'PY'
import json, os
from pathlib import Path
data = json.loads(Path("/tmp/out.json").read_text())
def v(k): return data.get(k, {}).get("value", "")
pw = os.environ["SQL_PASS"]
lines = [
    f"AZURE_STORAGE_ACCOUNT={v('storageAccountName')}",
    f"AZURE_DATA_FACTORY_NAME={v('dataFactoryName')}",
    f"AZURE_SQL_SERVER={v('sqlServerFqdn')}",
    f"AZURE_SQL_ADMIN_LOGIN={v('sqlAdminLogin')}",
    f"AZURE_SQL_OLIST_DATABASE={v('olistDatabaseName')}",
    f"AZURE_SQL_DW_DATABASE={v('olistDwDatabaseName')}",
    f"AZURE_SQL_ADMIN_PASSWORD={pw}",
    f"MSSQL_SA_PASSWORD={pw}",
]
Path(".env").write_text("\n".join(lines) + "\n")
print("Wrote .env")
PY
```

### 4. Seed Azure SQL

```bash
source .env
LOGIN="${AZURE_SQL_ADMIN_LOGIN:-olistadmin}"

for f in 01_create_olist_db.sql 02_seed_sample_data.sql 03_seed_bulk_orders.sql 04_create_olist_dw.sql; do
  echo "Running $f ..."
  sqlcmd -S "$AZURE_SQL_SERVER" -U "$LOGIN" -P "$AZURE_SQL_ADMIN_PASSWORD" -C -i "docker/sql/init/$f"
done
```

### 5. Publicar ADF

Cloud Shell inclui **PowerShell Core**:

```bash
pwsh -File docker/azure/publish-adf.ps1 -EnvFile .env
```

Publica linked services, datasets e pipelines (Copy nativo).

### 6. Executar pipeline master

```bash
source .env
RUN_ID=$(az datafactory pipeline create-run \
  --resource-group rg-olist-dev \
  --factory-name "$AZURE_DATA_FACTORY_NAME" \
  --name pl_olist_end_to_end \
  --query runId -o tsv)

echo "Run ID: $RUN_ID"
echo "Portal: https://adf.azure.com"
```

Acompanhar status:

```bash
az datafactory pipeline-run show \
  --resource-group rg-olist-dev \
  --factory-name "$AZURE_DATA_FACTORY_NAME" \
  --run-id "$RUN_ID" \
  --query "{status:status, duration:durationInMs}" -o table
```

---

## Verificar recursos

```bash
source ~/data-platform/.env 2>/dev/null || source .env

az group show -n rg-olist-dev -o table
az storage container list --account-name "$AZURE_STORAGE_ACCOUNT" --auth-mode login -o table
az datafactory show -g rg-olist-dev -n "$AZURE_DATA_FACTORY_NAME" -o table
```

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| `530035` no PC local | Normal — use Cloud Shell ou portal ADF |
| `sqlcmd: command not found` | Cloud Shell → **PowerShell** tab, ou `sudo apt install mssql-tools18` |
| Publish ADF falha senha | Confira `AZURE_SQL_ADMIN_PASSWORD` no `.env` |
| Pipeline falha no Copy | Portal ADF → run → activity error; confira linked service test |
| Re-deploy sem recriar SQL | `SKIP_INFRA=1` no script |

---

## Sincronizar `.env` no PC (opcional)

Copie os valores do `.env` gerado no Cloud Shell para sua máquina local (sem commitar):

```bash
cat ~/data-platform/.env
```

No Windows, cole em `.env` na raiz do repo para scripts locais (`azure-olist-transform`, etc.).

---

## Referências

- [azure-adf-setup.md](azure-adf-setup.md) — pipelines Copy nativo
- [secrets-pipeline.md](secrets-pipeline.md) — SOPS local
- Script: `docker/azure/cloudshell-deploy.sh`
