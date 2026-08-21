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

if ([string]::IsNullOrWhiteSpace($storageAccount)) {
    throw "AZURE_STORAGE_ACCOUNT not set in $EnvFile"
}
if ([string]::IsNullOrWhiteSpace($sqlServer)) {
    throw "AZURE_SQL_SERVER not set. Run infra deploy + sync-deploy-outputs.ps1"
}
if ([string]::IsNullOrWhiteSpace($sqlPassword)) {
    throw "AZURE_SQL_ADMIN_PASSWORD (or MSSQL_SA_PASSWORD) not set"
}

$adlsUrl = "https://$storageAccount.dfs.core.windows.net"
$olistConn = "Server=tcp:$sqlServer,1433;Initial Catalog=$olistDb;User ID=$sqlLogin;Password=$sqlPassword;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
$dwConn = "Server=tcp:$sqlServer,1433;Initial Catalog=$dwDb;User ID=$sqlLogin;Password=$sqlPassword;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"

Write-Host "Publishing ADF artifacts to $FactoryName ($ResourceGroup)..."

$lsAdls = (Get-Content (Join-Path $AdfRoot "linkedservices/ls_adls_olist.json") -Raw).Replace("__ADLS_URL__", "$adlsUrl/")
$lsAdlsObj = $lsAdls | ConvertFrom-Json
Publish-AdfResource -Kind linkedService -Name $lsAdlsObj.name -Properties $lsAdlsObj.properties

$lsOlist = (Get-Content (Join-Path $AdfRoot "linkedservices/ls_azure_sql_olist.json") -Raw).Replace("__AZURE_SQL_OLIST_CONNECTION__", $olistConn)
$lsOlistObj = $lsOlist | ConvertFrom-Json
Publish-AdfResource -Kind linkedService -Name $lsOlistObj.name -Properties $lsOlistObj.properties

$lsDw = (Get-Content (Join-Path $AdfRoot "linkedservices/ls_azure_sql_dw.json") -Raw).Replace("__AZURE_SQL_DW_CONNECTION__", $dwConn)
$lsDwObj = $lsDw | ConvertFrom-Json
Publish-AdfResource -Kind linkedService -Name $lsDwObj.name -Properties $lsDwObj.properties

Get-ChildItem (Join-Path $AdfRoot "datasets") -Filter "*.json" | ForEach-Object {
    $artifact = Read-JsonArtifact $_.FullName
    if ($artifact.name -eq "ds_sql_olist_table") { return }
    Publish-AdfResource -Kind dataset -Name $artifact.name -Properties $artifact.properties
}

Get-ChildItem (Join-Path $AdfRoot "pipelines") -Filter "*.json" | ForEach-Object {
    $artifact = Read-JsonArtifact $_.FullName
    Publish-AdfResource -Kind pipeline -Name $artifact.name -Properties $artifact.properties
}

Write-Host ""
Write-Host "ADF publish complete."
Write-Host "  Master pipeline: pl_olist_end_to_end"
Write-Host "  Trigger: make azure-olist-full"
