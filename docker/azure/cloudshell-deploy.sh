#!/usr/bin/env bash
# Full Olist deploy from Azure Cloud Shell (Bash).
# Usage:
#   export AZURE_SQL_ADMIN_PASSWORD='your-strong-password'
#   bash docker/azure/cloudshell-deploy.sh
#
# Optional:
#   SKIP_INFRA=1 SKIP_SEED=1 SKIP_PUBLISH=1 SKIP_PIPELINE=1
set -euo pipefail

REPO="${REPO:-https://github.com/VictorCappelletto/data-platform.git}"
BRANCH="${BRANCH:-publish-main}"
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-olist-dev}"
LOCATION="${LOCATION:-eastus}"
WORKDIR="${WORKDIR:-$HOME/data-platform}"
PIPELINE_NAME="${PIPELINE_NAME:-pl_olist_end_to_end}"

require_az() {
  az account show >/dev/null 2>&1 || {
    echo "Not logged in. Open https://portal.azure.com and launch Cloud Shell." >&2
    exit 1
  }
}

sql_password() {
  if [[ -n "${AZURE_SQL_ADMIN_PASSWORD:-}" ]]; then
    printf '%s' "$AZURE_SQL_ADMIN_PASSWORD"
    return
  fi
  if [[ -n "${MSSQL_SA_PASSWORD:-}" ]]; then
    printf '%s' "$MSSQL_SA_PASSWORD"
    return
  fi
  read -rsp "Azure SQL admin password: " _pw
  echo "" >&2
  printf '%s' "$_pw"
}

clone_repo() {
  if [[ -d "$WORKDIR/.git" ]]; then
    echo "Updating $WORKDIR ..."
    git -C "$WORKDIR" fetch origin "$BRANCH"
    git -C "$WORKDIR" checkout "$BRANCH"
    git -C "$WORKDIR" pull --ff-only origin "$BRANCH"
  else
    echo "Cloning $REPO ($BRANCH) ..."
    git clone --branch "$BRANCH" --depth 1 "$REPO" "$WORKDIR"
  fi
  cd "$WORKDIR"
}

write_env_from_deployment() {
  local deploy_name="$1"
  local out_json
  out_json="$(mktemp)"
  az deployment sub show --name "$deploy_name" --query properties.outputs -o json >"$out_json"
  python3 <<PY
import json
from pathlib import Path

data = json.loads(Path("$out_json").read_text())

def v(key):
    return data.get(key, {}).get("value", "")

lines = [
    f"AZURE_STORAGE_ACCOUNT={v('storageAccountName')}",
    f"AZURE_ADLS_ENDPOINT={v('adlsEndpoint')}",
    f"AZURE_DATA_FACTORY_NAME={v('dataFactoryName')}",
    f"AZURE_SQL_SERVER={v('sqlServerFqdn')}",
    f"AZURE_SQL_ADMIN_LOGIN={v('sqlAdminLogin')}",
    f"AZURE_SQL_OLIST_DATABASE={v('olistDatabaseName')}",
    f"AZURE_SQL_DW_DATABASE={v('olistDwDatabaseName')}",
    f"AZURE_SQL_ADMIN_PASSWORD={__import__('os').environ.get('_SQL_PASS', '')}",
    f"MSSQL_SA_PASSWORD={__import__('os').environ.get('_SQL_PASS', '')}",
]
Path(".env").write_text("\n".join(lines) + "\n")
for line in lines:
    key = line.split("=", 1)[0]
    val = line.split("=", 1)[1]
    if "PASSWORD" in key:
        val = "***"
    print(f"  {key}={val}")
PY
  rm -f "$out_json"
}

deploy_infra() {
  local deploy_name="cloudshell-$(date +%Y%m%d%H%M%S)"
  local pass
  pass="$(sql_password)"
  export _SQL_PASS="$pass"

  echo "What-if infra/main.bicep ..."
  az deployment sub what-if \
    --location "$LOCATION" \
    --template-file infra/main.bicep \
    --parameters infra/parameters/dev.bicepparam "sqlAdminPassword=$pass"

  echo "Deploying infra/main.bicep ($deploy_name) ..."
  az deployment sub create \
    --location "$LOCATION" \
    --template-file infra/main.bicep \
    --parameters infra/parameters/dev.bicepparam "sqlAdminPassword=$pass" \
    --name "$deploy_name"

  echo "Writing .env from deployment outputs ..."
  write_env_from_deployment "$deploy_name"
}

seed_sql() {
  # shellcheck disable=SC1091
  set -a && source .env && set +a
  local login="${AZURE_SQL_ADMIN_LOGIN:-olistadmin}"
  echo "Seeding Azure SQL: $AZURE_SQL_SERVER"
  for script in 01_create_olist_db.sql 02_seed_sample_data.sql 03_seed_bulk_orders.sql 04_create_olist_dw.sql; do
    echo "  $script"
    sqlcmd -S "$AZURE_SQL_SERVER" -U "$login" -P "$AZURE_SQL_ADMIN_PASSWORD" -C -i "docker/sql/init/$script"
  done
}

publish_adf() {
  if command -v pwsh >/dev/null 2>&1; then
    pwsh -File docker/azure/publish-adf.ps1 -EnvFile .env
  else
    echo "PowerShell not found — run publish steps manually (see docs/azure-cloudshell-deploy.md)" >&2
    exit 1
  fi
}

trigger_pipeline() {
  # shellcheck disable=SC1091
  set -a && source .env && set +a
  echo "Starting $PIPELINE_NAME on $AZURE_DATA_FACTORY_NAME ..."
  local run_id
  run_id="$(az datafactory pipeline create-run \
    --resource-group "$RESOURCE_GROUP" \
    --factory-name "$AZURE_DATA_FACTORY_NAME" \
    --name "$PIPELINE_NAME" \
    --query runId -o tsv)"
  echo "Run ID: $run_id"
  echo "Monitor: https://adf.azure.com"

  for _ in $(seq 1 180); do
    local status
    status="$(az datafactory pipeline-run show \
      --resource-group "$RESOURCE_GROUP" \
      --factory-name "$AZURE_DATA_FACTORY_NAME" \
      --run-id "$run_id" \
      --query status -o tsv)"
    echo "  Status: $status"
    [[ "$status" == "Succeeded" ]] && return 0
    [[ "$status" == "Failed" || "$status" == "Cancelled" ]] && return 1
    sleep 15
  done
  echo "Timed out waiting for pipeline" >&2
  return 1
}

main() {
  require_az
  clone_repo

  [[ "${SKIP_INFRA:-0}" == "1" ]] || deploy_infra
  [[ "${SKIP_SEED:-0}" == "1" ]] || seed_sql
  [[ "${SKIP_PUBLISH:-0}" == "1" ]] || publish_adf
  [[ "${SKIP_PIPELINE:-0}" == "1" ]] || trigger_pipeline

  echo ""
  echo "Done. Pipeline: $PIPELINE_NAME (Copy nativo end-to-end)"
}

main "$@"
