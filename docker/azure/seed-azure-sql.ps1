# Apply SQL init scripts to Azure SQL (olist source + olist_dw schemas).
param(
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path (Join-Path $repo "pyproject.toml"))) {
    $repo = (Split-Path $PSScriptRoot -Parent) | Split-Path -Parent
}

function Get-EnvValue {
    param([string]$Key)
    $path = Join-Path $repo $EnvFile
    if (Test-Path $path) {
        foreach ($line in Get-Content $path) {
            if ($line -match "^\s*$Key=(.*)$") {
                return $Matches[1].Trim()
            }
        }
    }
    return (Get-Item -Path "Env:$Key" -ErrorAction SilentlyContinue).Value
}

$server = Get-EnvValue "AZURE_SQL_SERVER"
$login = Get-EnvValue "AZURE_SQL_ADMIN_LOGIN"
if ([string]::IsNullOrWhiteSpace($login)) { $login = "olistadmin" }
$password = Get-EnvValue "AZURE_SQL_ADMIN_PASSWORD"
if ([string]::IsNullOrWhiteSpace($password)) { $password = Get-EnvValue "MSSQL_SA_PASSWORD" }

if ([string]::IsNullOrWhiteSpace($server) -or [string]::IsNullOrWhiteSpace($password)) {
    throw "AZURE_SQL_SERVER and AZURE_SQL_ADMIN_PASSWORD (or MSSQL_SA_PASSWORD) required"
}

$sqlInit = Join-Path $repo "docker\sql\init"
$scripts = @(
    "01_create_olist_db.sql",
    "02_seed_sample_data.sql",
    "03_seed_bulk_orders.sql",
    "04_create_olist_dw.sql"
)

Write-Host "Seeding Azure SQL: $server"

foreach ($script in $scripts) {
    $path = Join-Path $sqlInit $script
    if (-not (Test-Path $path)) {
        Write-Host "  SKIP missing $script"
        continue
    }
    Write-Host "  Running $script ..."
    sqlcmd -S $server -U $login -P $password -C -i $path
    if ($LASTEXITCODE -ne 0) {
        throw "sqlcmd failed on $script (exit $LASTEXITCODE)"
    }
}

Write-Host "Azure SQL seed complete."
