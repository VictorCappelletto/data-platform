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

function Invoke-AzureSqlScript {
    param(
        [string]$Path,
        [string]$Database
    )
    # Azure SQL does not support USE; databases are created by Bicep deploy.
    $content = Get-Content $Path -Raw
    $content = $content -replace '(?s)IF DB_ID\(N''[^'']+''\) IS NULL\s*BEGIN\s*CREATE DATABASE [^;]+;\s*END\s*GO\s*', ''
    $content = $content -replace '(?m)^USE\s+\w+\s*;\s*\r?\nGO\s*\r?\n', ''

    $tempFile = Join-Path $env:TEMP ("azure-sql-" + [guid]::NewGuid().ToString() + ".sql")
    Set-Content -Path $tempFile -Value $content -Encoding utf8
    try {
        sqlcmd -S $server -U $login -P $password -C -d $Database -i $tempFile
        if ($LASTEXITCODE -ne 0) {
            throw "sqlcmd failed (exit $LASTEXITCODE)"
        }
    } finally {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
    }
}

foreach ($script in $scripts) {
    $path = Join-Path $sqlInit $script
    if (-not (Test-Path $path)) {
        Write-Host "  SKIP missing $script"
        continue
    }
    $database = if ($script -eq "04_create_olist_dw.sql") { "olist_dw" } else { "olist" }
    Write-Host "  Running $script on $database ..."
    Invoke-AzureSqlScript -Path $path -Database $database
}

Write-Host "Azure SQL seed complete."
