# Run processing + curated + publish on ADLS landing (after ADF copy).
param(
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path (Join-Path $repo "pyproject.toml"))) {
    $repo = (Split-Path $PSScriptRoot -Parent) | Split-Path -Parent
}

if (Test-Path (Join-Path $repo $EnvFile)) {
    Get-Content (Join-Path $repo $EnvFile) | ForEach-Object {
        if ($_ -match "^\s*([^#=]+)=(.*)$") {
            [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), "Process")
        }
    }
}

$env:DATA_PLATFORM_ROOT = $repo
$env:DATA_PLATFORM_APP = "ingestion_azure"
$env:LAKE_ROOT = Join-Path $repo "data\lake"
$env:OLIST_LAKE_BACKEND = "adls"
$env:OLIST_PROCESSING_ENGINE = "local"

if (-not $env:AZURE_STORAGE_ACCOUNT) {
    throw "AZURE_STORAGE_ACCOUNT not set in $EnvFile"
}

Write-Host "Olist pipeline (from landing) via orchestrator"
Write-Host "  Storage: $($env:AZURE_STORAGE_ACCOUNT)"

Set-Location (Join-Path $repo "apps\ingestion_azure")
python workflows/runs/olist_demo.py --mode transform_from_landing
