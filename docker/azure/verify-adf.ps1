# Verify Azure Data Factory + artifacts exist.
param(
    [string]$ResourceGroup = "rg-olist-dev",
    [string]$FactoryName = "",
    [string]$EnvFile = ".env"
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

if ([string]::IsNullOrWhiteSpace($FactoryName)) {
    $FactoryName = Get-EnvValue "AZURE_DATA_FACTORY_NAME"
}
if ([string]::IsNullOrWhiteSpace($FactoryName)) {
    throw "AZURE_DATA_FACTORY_NAME not set"
}

Write-Host "Checking Data Factory: $FactoryName ($ResourceGroup)"

$factory = az datafactory show --resource-group $ResourceGroup --factory-name $FactoryName -o json | ConvertFrom-Json
Write-Host "  Factory state: $($factory.provisioningState)"
Write-Host "  Location: $($factory.location)"
Write-Host "  MI principal: $($factory.identity.principalId)"

$expected = @{
    integrationRuntime = @("shir-olist-dev")
    linkedService      = @("ls_adls_olist")
    dataset            = @("ds_adls_landing_csv")
    pipeline           = @()
}

# Optional SQL artifacts (after SHIR online + full publish)
$ErrorActionPreference = "Continue"
az datafactory linked-service show `
    --resource-group $ResourceGroup `
    --factory-name $FactoryName `
    --linked-service-name ls_sql_olist `
    --only-show-errors 2>$null | Out-Null
$sqlReady = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = "Stop"

if ($sqlReady) {
    $expected.linkedService += "ls_sql_olist"
    $expected.dataset += "ds_sql_olist_table"
    $expected.pipeline += "pl_olist_landing_copy"
}

foreach ($kind in $expected.Keys) {
    $listCmd = switch ($kind) {
        "integrationRuntime" { @("datafactory", "integration-runtime", "list") }
        "linkedService"      { @("datafactory", "linked-service", "list") }
        "dataset"            { @("datafactory", "dataset", "list") }
        "pipeline"           { @("datafactory", "pipeline", "list") }
    }
    $items = az @listCmd --resource-group $ResourceGroup --factory-name $FactoryName -o json | ConvertFrom-Json
    $names = @($items | ForEach-Object { $_.name })
    foreach ($name in $expected[$kind]) {
        if ($names -contains $name) {
            Write-Host "  OK $kind $name"
        } else {
            if ($expected[$kind].Count -eq 0) { continue }
            throw "Missing $kind $name. Run publish-adf.ps1"
        }
    }
}

$ErrorActionPreference = "Continue"
$irStatus = az datafactory integration-runtime get-status `
    --resource-group $ResourceGroup `
    --factory-name $FactoryName `
    --integration-runtime-name shir-olist-dev `
    --query "typeProperties.status" -o tsv 2>$null
$ErrorActionPreference = "Stop"

if ($irStatus) {
    Write-Host "  SHIR state: $irStatus"
    if ($irStatus -ne "Online") {
        Write-Host "  WARN: Self-hosted IR not online. SQL copy will fail until setup-shir.ps1 completes"
    }
} else {
    Write-Host "  WARN: Self-hosted IR not registered. Run setup-shir.ps1 (Phase 5)"
}

Write-Host ""
Write-Host "ADF verification OK"
