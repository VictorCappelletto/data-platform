# Initialize SQL Server (Docker) with Olist schema + mock data.
# Usage: .\docker\sql\setup.ps1
param(
    [string]$Server = "localhost,1433",
    [string]$User = "sa",
    [string]$Password = $env:MSSQL_SA_PASSWORD,
    [switch]$UseDocker
)

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not $Password) {
    $Password = "Olist@Dev123!"
}

function Invoke-SqlFile {
    param([string]$FilePath)
    Write-Host "Running $FilePath ..."
    if ($UseDocker) {
        $container = "data-platform-sqlserver"
        Get-Content $FilePath -Raw | docker exec -i $container /opt/mssql-tools18/bin/sqlcmd -S localhost -U $User -P $Password -C
    } else {
        sqlcmd -S $Server -U $User -P $Password -C -i $FilePath
    }
    if ($LASTEXITCODE -ne 0) { throw "sqlcmd failed for $FilePath" }
}

function Wait-SqlServer {
    param([int]$MaxAttempts = 30)
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            if ($UseDocker) {
                docker exec data-platform-sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -U $User -P $Password -C -Q "SELECT 1" | Out-Null
            } else {
                sqlcmd -S $Server -U $User -P $Password -C -Q "SELECT 1" | Out-Null
            }
            if ($LASTEXITCODE -eq 0) {
                Write-Host "SQL Server is ready."
                return
            }
        } catch {
            # retry
        }
        Write-Host "Waiting for SQL Server ($i/$MaxAttempts)..."
        Start-Sleep -Seconds 3
    }
    throw "SQL Server did not become ready in time."
}

Push-Location $Root
try {
    if ($UseDocker) {
        Write-Host "Starting SQL Server container..."
        docker compose up -d sqlserver
        Wait-SqlServer
    } else {
        Wait-SqlServer
    }

    $initDir = Join-Path $PSScriptRoot "init"
    Get-ChildItem $initDir -Filter "*.sql" | Sort-Object Name | ForEach-Object {
        Invoke-SqlFile -FilePath $_.FullName
    }

    Write-Host ""
    Write-Host "Olist database ready."
    Write-Host "  Server: $Server"
    Write-Host "  Database: olist"
    Write-Host "  User: $User"
} finally {
    Pop-Location
}
