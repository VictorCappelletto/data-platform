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
            "integrationRuntime" {
                az datafactory integration-runtime self-hosted create `
                    --resource-group $ResourceGroup `
                    --factory-name $FactoryName `
                    --name $Name `
                    --description "Self-hosted IR for local SQL Server (Olist)" `
                    --only-show-errors
                if ($LASTEXITCODE -ne 0) { throw "integration-runtime create failed: $Name" }
            }
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
if ([string]::IsNullOrWhiteSpace($storageAccount)) {
    throw "AZURE_STORAGE_ACCOUNT not set in $EnvFile"
}

$adlsUrl = "https://$storageAccount.dfs.core.windows.net"
$sqlServer = Get-EnvValue "MSSQL_SERVER"
$sqlDatabase = Get-EnvValue "MSSQL_DATABASE"
$sqlUser = Get-EnvValue "MSSQL_USER"
$sqlPassword = Get-EnvValue "MSSQL_SA_PASSWORD"
if ([string]::IsNullOrWhiteSpace($sqlPassword)) {
    throw "MSSQL_SA_PASSWORD not set. Use secrets pipeline or .env"
}

$sqlConn = "Server=$sqlServer;Database=$sqlDatabase;User Id=$sqlUser;Password=$sqlPassword;TrustServerCertificate=True;Encrypt=False"

Write-Host "Publishing ADF artifacts to $FactoryName ($ResourceGroup)..."

$irStatus = az datafactory integration-runtime get-status `
    --resource-group $ResourceGroup `
    --factory-name $FactoryName `
    --integration-runtime-name shir-olist-dev `
    --query "properties.state" -o tsv 2>$null

if ($irStatus -ne "Online") {
    Write-Host "  WARN: SHIR not Running (status=$irStatus). SQL linked service skipped."
    Write-Host "        Run setup-shir.ps1 then re-run publish-adf.ps1"
    $skipSql = $true
} else {
    $skipSql = $false
}

# Integration Runtime (Self-hosted — register with setup-shir.ps1)
try {
    az datafactory integration-runtime show `
        --resource-group $ResourceGroup `
        --factory-name $FactoryName `
        --integration-runtime-name shir-olist-dev `
        --only-show-errors | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK integrationRuntime shir-olist-dev (exists)"
    }
} catch {
    Publish-AdfResource -Kind integrationRuntime -Name "shir-olist-dev" -Properties @{}
}

# Linked services (substitute placeholders)
$lsAdls = Get-Content (Join-Path $AdfRoot "linkedservices/ls_adls_olist.json") -Raw
$lsAdls = $lsAdls.Replace("__ADLS_URL__", "$adlsUrl/")
$lsAdlsObj = $lsAdls | ConvertFrom-Json
Publish-AdfResource -Kind linkedService -Name $lsAdlsObj.name -Properties $lsAdlsObj.properties

if (-not $skipSql) {
    $lsSql = Get-Content (Join-Path $AdfRoot "linkedservices/ls_sql_olist.json") -Raw
    $lsSql = $lsSql.Replace("__SQL_CONNECTION_STRING__", $sqlConn)
    $lsSqlObj = $lsSql | ConvertFrom-Json
    Publish-AdfResource -Kind linkedService -Name $lsSqlObj.name -Properties $lsSqlObj.properties
} else {
    Write-Host "  SKIP linkedService ls_sql_olist (SHIR offline)"
}

# Datasets
Get-ChildItem (Join-Path $AdfRoot "datasets") -Filter "*.json" | ForEach-Object {
    $artifact = Read-JsonArtifact $_.FullName
    if ($skipSql -and $artifact.name -eq "ds_sql_olist_table") {
        Write-Host "  SKIP dataset ds_sql_olist_table (SHIR offline)"
        return
    }
    Publish-AdfResource -Kind dataset -Name $artifact.name -Properties $artifact.properties
}

# Pipelines
if (-not $skipSql) {
    Get-ChildItem (Join-Path $AdfRoot "pipelines") -Filter "*.json" | ForEach-Object {
        $artifact = Read-JsonArtifact $_.FullName
        Publish-AdfResource -Kind pipeline -Name $artifact.name -Properties $artifact.properties
    }
} else {
    Write-Host "  SKIP pipeline pl_olist_landing_copy (requires SQL linked service + SHIR)"
}

Write-Host ""
Write-Host "ADF publish complete."
Write-Host "  Factory: $FactoryName"
Write-Host "  Pipeline: pl_olist_landing_copy"
Write-Host ""
Write-Host "Next: register Self-hosted IR (Phase 5):"
Write-Host "  powershell -ExecutionPolicy Bypass -File docker/azure/setup-shir.ps1"
