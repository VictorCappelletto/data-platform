# Verify Azure resource group matches encrypted .env variables.
param(
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

function Get-EnvValue {
    param([string]$Name, [string]$Path)
    if (-not (Test-Path $Path)) {
        throw "Env file not found: $Path (run: make env-prepare)"
    }
    foreach ($line in Get-Content $Path) {
        if ($line -match "^\s*$Name=(.*)$") {
            return $Matches[1].Trim()
        }
    }
    throw "Variable not set in ${Path}: $Name"
}

$rgName = Get-EnvValue -Name "AZURE_RESOURCE_GROUP" -Path $EnvFile
$expectedLocation = Get-EnvValue -Name "AZURE_LOCATION" -Path $EnvFile
$expectedSub = Get-EnvValue -Name "AZURE_SUBSCRIPTION_ID" -Path $EnvFile

Write-Host "Checking Azure resource group from $EnvFile ..."
Write-Host "  AZURE_RESOURCE_GROUP = $rgName"
Write-Host "  AZURE_LOCATION       = $expectedLocation"
Write-Host "  AZURE_SUBSCRIPTION_ID= $expectedSub"
Write-Host ""

$account = az account show --query "{subscriptionId:id, name:name}" -o json 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Azure CLI not logged in. Run: az login"
}
Write-Host "Logged in: $account"

$rg = az group show --name $rgName -o json 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Resource group not found: $rgName"
}

$rgObj = $rg | ConvertFrom-Json
$actualLocation = $rgObj.location
$state = $rgObj.properties.provisioningState
$tags = $rgObj.tags

Write-Host ""
Write-Host "Resource group OK:"
Write-Host "  name     = $($rgObj.name)"
Write-Host "  location = $actualLocation"
Write-Host "  state    = $state"
Write-Host "  tags     = $($tags | ConvertTo-Json -Compress)"

if ($actualLocation -ne $expectedLocation) {
    throw "Location mismatch: expected $expectedLocation, got $actualLocation"
}

Write-Host ""
Write-Host "Verification passed."
