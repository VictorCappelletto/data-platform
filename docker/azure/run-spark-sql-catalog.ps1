# Register Spark SQL customers_db tables over lake paths.
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
$env:OLIST_PROCESSING_ENGINE = "spark"
if (-not $env:OLIST_LAKE_BACKEND) {
    $env:OLIST_LAKE_BACKEND = "local"
}

Write-Host "Spark SQL catalog via orchestrator"

Set-Location (Join-Path $repo "apps\ingestion_azure")
python workflows/runs/olist_demo.py --mode sql_catalog
