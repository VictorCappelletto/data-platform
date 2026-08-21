# OIDC para GitHub Actions — via Azure Cloud Shell (browser)

O `az login` local está bloqueado (530035). O **Cloud Shell** no portal usa autenticação do browser e funciona.

## 1. Abrir Cloud Shell

1. [portal.azure.com](https://portal.azure.com)
2. Ícone **`>_`** (topo) → **Bash**
3. Cole e execute o bloco abaixo (ajusta branch `publish-main`):

```bash
APP_NAME="sp-data-platform-github"
GITHUB_REPO="VictorCappelletto/data-platform"
GITHUB_BRANCH="publish-main"
RG="rg-olist-dev"
SUB="$(az account show --query id -o tsv)"
TENANT="$(az account show --query tenantId -o tsv)"
SCOPE="/subscriptions/${SUB}/resourceGroups/${RG}"

APP_ID="$(az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv)"
if [ -z "$APP_ID" ]; then
  APP_ID="$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)"
  echo "Created app: $APP_ID"
else
  echo "App exists: $APP_ID"
fi

az ad sp list --filter "appId eq '$APP_ID'" --query "[0].id" -o tsv | grep -q . \
  || az ad sp create --id "$APP_ID" >/dev/null

SUBJECT="repo:${GITHUB_REPO}:ref:refs/heads/${GITHUB_BRANCH}"
FC_NAME="github-data-platform-publish-main"
EXISTS="$(az ad app federated-credential list --id "$APP_ID" --query "[?subject=='$SUBJECT'].name" -o tsv)"
if [ -z "$EXISTS" ]; then
  az ad app federated-credential create --id "$APP_ID" --parameters "{
    \"name\": \"$FC_NAME\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"$SUBJECT\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"
  echo "Created federated credential"
else
  echo "Federated credential exists: $EXISTS"
fi

az role assignment list --assignee "$APP_ID" --scope "$SCOPE" --role Contributor -o tsv | grep -q . \
  || az role assignment create --assignee "$APP_ID" --role Contributor --scope "$SCOPE"

echo ""
echo "=== Copie para GitHub Secrets ==="
echo "AZURE_CLIENT_ID=$APP_ID"
echo "AZURE_TENANT_ID=$TENANT"
echo "AZURE_SUBSCRIPTION_ID=$SUB"
```

## 2. GitHub Secrets (no PC local)

No terminal do projeto (só `gh` — não precisa de `az`):

```powershell
gh secret set AZURE_CLIENT_ID --body "<client-id-do-cloud-shell>" -R VictorCappelletto/data-platform
gh secret set AZURE_TENANT_ID --body "3950d3d0-769c-4153-a41d-c02adbfe1f35" -R VictorCappelletto/data-platform
gh secret set AZURE_SUBSCRIPTION_ID --body "82700697-643d-4ea8-aebe-57c85a333594" -R VictorCappelletto/data-platform
gh secret set AZURE_SQL_ADMIN_PASSWORD --body "<sua-senha-sql>" -R VictorCappelletto/data-platform
```

Opcional: `SOPS_AGE_KEY` se usar secrets encriptados no CI.

## 3. Disparar deploy

```powershell
gh workflow run azure-olist-deploy -R VictorCappelletto/data-platform --ref publish-main
gh run watch -R VictorCappelletto/data-platform
```

Ou: GitHub → **Actions** → **azure-olist-deploy** → **Run workflow**.

## O que o workflow faz

1. Deploy Bicep (ADLS + ADF + SQL + ACR + Batch)
2. Seed Azure SQL
3. Build/push imagem `olist-transform`
4. Publish ADF (Custom Activity)
5. Trigger `pl_olist_end_to_end`
