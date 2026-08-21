# Publish ADF artifacts (linked services, datasets, pipelines) from infra/adf/.
param(
    [string]$ResourceGroup = "rg-olist-dev",
    [string]$FactoryName = "",
    [string]$EnvFile = ".env",
    [string]$AdfRoot = "infra/adf"
)

$ErrorActionPreference = "Stop"

function Get-EnvValue {
    param([string]$Key)
    if (Test-Path $EnvFile) {
        foreach ($line in Get-Content $EnvFile) {
            if ($line -match "^\s*$Key=(.*)$") {
                return $Matches[1].Trim()
            }
        }
    }
    return (Get-Item -Path "Env:$Key" -ErrorAction SilentlyContinue).Value
}

function Read-JsonArtifact {
    param([string]$Path)
    Get-Content $Path -Raw | ConvertFrom-Json
}

function Publish-AdfResource {
    param(
        [string]$Kind,
        [string]$Name,
        [object]$Properties
    )
    $propsFile = Join-Path $env:TEMP ("adf-props-" + [guid]::NewGuid().ToString() + ".json")
    ($Properties | ConvertTo-Json -Depth 50) | Set-Content $propsFile -Encoding utf8
    try {
        switch ($Kind) {
            "linkedService" {
                az datafactory linked-service create `
                    --resource-group $ResourceGroup `
                    --factory-name $FactoryName `
                    --linked-service-name $Name `
                    --properties "@$propsFile" `
                    --only-show-errors
                if ($LASTEXITCODE -ne 0) { throw "linked-service create failed: $Name" }
            }
            "dataset" {
                az datafactory dataset create `
                    --resource-group $ResourceGroup `
                    --factory-name $FactoryName `
                    --dataset-name $Name `
                    --properties "@$propsFile" `
                    --only-show-errors
                if ($LASTEXITCODE -ne 0) { throw "dataset create failed: $Name" }
            }
            "pipeline" {
                az datafactory pipeline create `
                    --resource-group $ResourceGroup `
                    --factory-name $FactoryName `
                    --pipeline-name $Name `
                    --pipeline "@$propsFile" `
                    --only-show-errors
                if ($LASTEXITCODE -ne 0) { throw "pipeline create failed: $Name" }
            }
            default { throw "Unknown kind: $Kind" }
        }
        Write-Host "  OK $Kind $Name"
    } finally {
        Remove-Item $propsFile -Force -ErrorAction SilentlyContinue
    }
}

if ([string]::IsNullOrWhiteSpace($FactoryName)) {
    $FactoryName = Get-EnvValue "AZURE_DATA_FACTORY_NAME"
}
if ([string]::IsNullOrWhiteSpace($FactoryName)) {
    throw "AZURE_DATA_FACTORY_NAME not set. Run infra deploy + sync-deploy-outputs.ps1"
}

$storageAccount = Get-EnvValue "AZURE_STORAGE_ACCOUNT"
$sqlServer = Get-EnvValue "AZURE_SQL_SERVER"
$sqlLogin = Get-EnvValue "AZURE_SQL_ADMIN_LOGIN"
if ([string]::IsNullOrWhiteSpace($sqlLogin)) { $sqlLogin = "olistadmin" }
$sqlPassword = Get-EnvValue "AZURE_SQL_ADMIN_PASSWORD"
if ([string]::IsNullOrWhiteSpace($sqlPassword)) {
    $sqlPassword = Get-EnvValue "MSSQL_SA_PASSWORD"
}
$olistDb = Get-EnvValue "AZURE_SQL_OLIST_DATABASE"
if ([string]::IsNullOrWhiteSpace($olistDb)) { $olistDb = "olist" }
$dwDb = Get-EnvValue "AZURE_SQL_DW_DATABASE"
if ([string]::IsNullOrWhiteSpace($dwDb)) { $dwDb = "olist_dw" }

$acrLogin = Get-EnvValue "AZURE_ACR_LOGIN_SERVER"
$batchAccount = Get-EnvValue "AZURE_BATCH_ACCOUNT_NAME"
$batchUri = Get-EnvValue "AZURE_BATCH_ACCOUNT_URL"
$batchPool = Get-EnvValue "AZURE_BATCH_POOL_NAME"
$batchStorage = Get-EnvValue "AZURE_BATCH_STORAGE_ACCOUNT_NAME"
$batchIdentityClientId = Get-EnvValue "AZURE_BATCH_POOL_IDENTITY_CLIENT_ID"
$transformImage = Get-EnvValue "AZURE_TRANSFORM_IMAGE"
if ([string]::IsNullOrWhiteSpace($transformImage)) { $transformImage = "olist-transform:latest" }

if ([string]::IsNullOrWhiteSpace($storageAccount)) {
    throw "AZURE_STORAGE_ACCOUNT not set in $EnvFile"
}
if ([string]::IsNullOrWhiteSpace($sqlServer)) {
    throw "AZURE_SQL_SERVER not set. Run infra deploy + sync-deploy-outputs.ps1"
}
if ([string]::IsNullOrWhiteSpace($sqlPassword)) {
    throw "AZURE_SQL_ADMIN_PASSWORD (or MSSQL_SA_PASSWORD) not set"
}
if ([string]::IsNullOrWhiteSpace($acrLogin) -or [string]::IsNullOrWhiteSpace($batchAccount)) {
    throw "Batch/ACR outputs missing. Run: make azure-infra-deploy"
}

$adlsUrl = "https://$storageAccount.dfs.core.windows.net"
$olistConn = "Server=tcp:$sqlServer,1433;Initial Catalog=$olistDb;User ID=$sqlLogin;Password=$sqlPassword;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
$dwConn = "Server=tcp:$sqlServer,1433;Initial Catalog=$dwDb;User ID=$sqlLogin;Password=$sqlPassword;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"

Write-Host "Fetching Batch/ACR credentials..."
$batchKey = az batch account keys list --name $batchAccount --resource-group $ResourceGroup --query primary -o tsv
if ($LASTEXITCODE -ne 0) { throw "Failed to list Batch account keys" }
$acrName = ($acrLogin -replace '\.azurecr\.io$', '')
$acrUser = az acr credential show --name $acrName --query username -o tsv
$acrPass = az acr credential show --name $acrName --query "passwords[0].value" -o tsv
if ($LASTEXITCODE -ne 0) { throw "Failed to read ACR credentials" }
$batchStorageKey = az storage account keys list --account-name $batchStorage --resource-group $ResourceGroup --query "[0].value" -o tsv
if ($LASTEXITCODE -ne 0) { throw "Failed to read Batch staging storage key" }
$batchStorageConn = "DefaultEndpointsProtocol=https;AccountName=$batchStorage;AccountKey=$batchStorageKey;EndpointSuffix=core.windows.net"

if ([string]::IsNullOrWhiteSpace($batchUri)) {
    $batchUri = "https://$batchAccount.eastus.batch.azure.com"
}
if ([string]::IsNullOrWhiteSpace($batchPool)) {
    $batchPool = "olist-pool"
}

$fullTransformImage = if ($transformImage -match '/') { $transformImage } else { "$acrLogin/$transformImage" }

Write-Host "Publishing ADF artifacts to $FactoryName ($ResourceGroup)..."

# Linked services — lake + SQL
$lsAdls = (Get-Content (Join-Path $AdfRoot "linkedservices/ls_adls_olist.json") -Raw).Replace("__ADLS_URL__", "$adlsUrl/")
Publish-AdfResource -Kind linkedService -Name "ls_adls_olist" -Properties (($lsAdls | ConvertFrom-Json).properties)

$lsOlist = (Get-Content (Join-Path $AdfRoot "linkedservices/ls_azure_sql_olist.json") -Raw).Replace("__AZURE_SQL_OLIST_CONNECTION__", $olistConn)
Publish-AdfResource -Kind linkedService -Name "ls_azure_sql_olist" -Properties (($lsOlist | ConvertFrom-Json).properties)

$lsDw = (Get-Content (Join-Path $AdfRoot "linkedservices/ls_azure_sql_dw.json") -Raw).Replace("__AZURE_SQL_DW_CONNECTION__", $dwConn)
Publish-AdfResource -Kind linkedService -Name "ls_azure_sql_dw" -Properties (($lsDw | ConvertFrom-Json).properties)

# Linked services — Batch + ACR (Custom Activity)
$lsBatchStorage = (Get-Content (Join-Path $AdfRoot "linkedservices/ls_batch_staging_storage.json") -Raw).Replace("__BATCH_STORAGE_CONNECTION_STRING__", $batchStorageConn)
Publish-AdfResource -Kind linkedService -Name "ls_batch_staging_storage" -Properties (($lsBatchStorage | ConvertFrom-Json).properties)

$lsAcr = (Get-Content (Join-Path $AdfRoot "linkedservices/ls_acr_olist.json") -Raw `
    ).Replace("__ACR_LOGIN_SERVER__", $acrLogin `
    ).Replace("__ACR_USERNAME__", $acrUser `
    ).Replace("__ACR_PASSWORD__", $acrPass)
Publish-AdfResource -Kind linkedService -Name "ls_acr_olist" -Properties (($lsAcr | ConvertFrom-Json).properties)

$lsBatch = (Get-Content (Join-Path $AdfRoot "linkedservices/ls_azure_batch.json") -Raw `
    ).Replace("__BATCH_ACCOUNT_NAME__", $batchAccount `
    ).Replace("__BATCH_ACCESS_KEY__", $batchKey `
    ).Replace("__BATCH_URI__", $batchUri `
    ).Replace("__BATCH_POOL_NAME__", $batchPool)
Publish-AdfResource -Kind linkedService -Name "ls_azure_batch" -Properties (($lsBatch | ConvertFrom-Json).properties)

# Datasets
Get-ChildItem (Join-Path $AdfRoot "datasets") -Filter "*.json" | ForEach-Object {
    $artifact = Read-JsonArtifact $_.FullName
    if ($artifact.name -eq "ds_sql_olist_table") { return }
    Publish-AdfResource -Kind dataset -Name $artifact.name -Properties $artifact.properties
}

# Pipelines (substitute Custom Activity placeholders)
$pipelineReplacements = @{
    "__AZURE_STORAGE_ACCOUNT__" = $storageAccount
    "__TRANSFORM_IMAGE__" = $fullTransformImage
    "__BATCH_POOL_IDENTITY_CLIENT_ID__" = $batchIdentityClientId
    "__AZURE_SQL_SERVER__" = $sqlServer
    "__AZURE_SQL_ADMIN_LOGIN__" = $sqlLogin
    "__AZURE_SQL_ADMIN_PASSWORD__" = $sqlPassword
}

Get-ChildItem (Join-Path $AdfRoot "pipelines") -Filter "*.json" | ForEach-Object {
    $raw = Get-Content $_.FullName -Raw
    foreach ($key in $pipelineReplacements.Keys) {
        $raw = $raw.Replace($key, $pipelineReplacements[$key])
    }
    $artifact = $raw | ConvertFrom-Json
    Publish-AdfResource -Kind pipeline -Name $artifact.name -Properties $artifact.properties
}

Write-Host ""
Write-Host "ADF publish complete."
Write-Host "  Image: $fullTransformImage"
Write-Host "  Master pipeline: pl_olist_end_to_end"
Write-Host "  Trigger: make azure-olist-full"
