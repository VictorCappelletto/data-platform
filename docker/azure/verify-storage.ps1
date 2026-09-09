# Verify ADLS Gen2 storage deployed in rg-olist-dev.
param(
    [string]$EnvFile = ".env",
    [string]$ResourceGroup = "",
    [string[]]$ExpectedContainers = @("landing", "processing", "curated")
)

$ErrorActionPreference = "Stop"

function Get-EnvValue {
    param([string]$Name, [string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    foreach ($line in Get-Content $Path) {
        if ($line -match "^\s*$Name=(.*)$") { return $Matches[1].Trim() }
    }
    return $null
}

if ([string]::IsNullOrWhiteSpace($ResourceGroup)) {
    $ResourceGroup = Get-EnvValue "AZURE_RESOURCE_GROUP" $EnvFile
    if (-not $ResourceGroup) { $ResourceGroup = "rg-olist-dev" }
}

$storageName = Get-EnvValue "AZURE_STORAGE_ACCOUNT" $EnvFile
if ([string]::IsNullOrWhiteSpace($storageName)) {
    throw "AZURE_STORAGE_ACCOUNT not in ${EnvFile} - run deploy first or set manually"
}

Write-Host "Checking storage account: $storageName (RG: $ResourceGroup)"
Write-Host ""

$account = az storage account show --name $storageName --resource-group $ResourceGroup -o json 2>&1
if ($LASTEXITCODE -ne 0) { throw "Storage account not found: $storageName" }

$acct = $account | ConvertFrom-Json
Write-Host "Storage OK:"
Write-Host "  name           = $($acct.name)"
Write-Host "  location       = $($acct.location)"
Write-Host "  sku            = $($acct.sku.name)"
Write-Host "  hns (ADLS Gen2)= $($acct.isHnsEnabled)"
Write-Host "  shared key     = $($acct.allowSharedKeyAccess)"
Write-Host "  dfs endpoint   = $($acct.primaryEndpoints.dfs)"
Write-Host ""

Write-Host "Containers:"
$subId = az account show --query id -o tsv
$containerBase = "/subscriptions/$subId/resourceGroups/$ResourceGroup/providers/Microsoft.Storage/storageAccounts/$storageName/blobServices/default/containers"
foreach ($name in $ExpectedContainers) {
    $id = "$containerBase/$name"
    $exists = az resource show --ids $id --query name -o tsv 2>$null
    if ($exists -eq $name) {
        Write-Host "  [ok] $name"
    } else {
        throw "Missing container: $name"
    }
}

Write-Host ""
Write-Host "Storage verification passed."
