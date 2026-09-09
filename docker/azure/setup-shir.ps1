# Install and register Self-hosted Integration Runtime for local SQL Server (Phase 5 bridge).
param(
    [string]$ResourceGroup = "rg-olist-dev",
    [string]$FactoryName = "",
    [string]$IntegrationRuntimeName = "shir-olist-dev",
    [string]$EnvFile = ".env",
    [string]$InstallDir = "$env:ProgramFiles\Microsoft Integration Runtime"
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

Write-Host "Fetching SHIR registration key for $IntegrationRuntimeName..."
$keyJson = az datafactory integration-runtime list-auth-key `
    --resource-group $ResourceGroup `
    --factory-name $FactoryName `
    --integration-runtime-name $IntegrationRuntimeName `
    -o json | ConvertFrom-Json

$key = $keyJson.authKey1
if ([string]::IsNullOrWhiteSpace($key)) {
    throw "Could not retrieve auth key. Ensure IR exists (publish-adf.ps1)"
}

$msiUrl = "https://www.microsoft.com/en-us/download/details.aspx?id=39717"
$msiPath = Join-Path $env:TEMP "IntegrationRuntime.msi"
$dmgcmd = $null

foreach ($candidate in @(
    (Join-Path $InstallDir "5.0\Shared\dmgcmd.exe"),
    (Join-Path $InstallDir "5.0\GatewaySetup.exe")
)) {
    if (Test-Path $candidate) { $dmgcmd = $candidate; break }
}
if (-not $dmgcmd -and (Test-Path $InstallDir)) {
    $dmgcmd = Get-ChildItem -Path $InstallDir -Recurse -Filter "dmgcmd.exe" -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
}

if (-not $dmgcmd) {
    Write-Host "Installing Microsoft Integration Runtime via winget..."
    winget install Microsoft.IntegrationRuntime `
        --accept-package-agreements `
        --accept-source-agreements `
        --disable-interactivity
    if ($LASTEXITCODE -ne 0) {
        Write-Host "winget install failed. Manual download: $msiUrl"
    }
    Start-Sleep -Seconds 15
    foreach ($candidate in @(
        (Join-Path $InstallDir "5.0\Shared\dmgcmd.exe"),
        (Join-Path $InstallDir "5.0\GatewaySetup.exe")
    )) {
        if (Test-Path $candidate) { $dmgcmd = $candidate; break }
    }
    if (-not $dmgcmd -and (Test-Path $InstallDir)) {
        $dmgcmd = Get-ChildItem -Path $InstallDir -Recurse -Filter "dmgcmd.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty FullName
    }
}

if (-not $dmgcmd) {
    Write-Host ""
    Write-Host "Integration Runtime installed. Register manually:"
    Write-Host "  1. Open ConfigManager.exe from Start Menu"
    Write-Host "  2. Paste auth key from: az datafactory integration-runtime list-auth-key ..."
    exit 1
}

$existingNodes = az datafactory integration-runtime get-status `
    --resource-group $ResourceGroup `
    --factory-name $FactoryName `
    --integration-runtime-name $IntegrationRuntimeName `
    --query "properties.nodes" -o json 2>$null | ConvertFrom-Json

if ($existingNodes -and $existingNodes.Count -gt 0) {
    Write-Host "  Node already registered: $($existingNodes[0].nodeName) ($($existingNodes[0].status))"
} else {
    Write-Host "Registering node with dmgcmd (admin required)..."
    $regArgs = "-RegisterNewNode `"$key`" olist-dev-node"
    $proc = Start-Process -FilePath $dmgcmd -ArgumentList $regArgs -Verb RunAs -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        throw "dmgcmd registration failed (exit $($proc.ExitCode)). Run PowerShell as Administrator and retry setup-shir.ps1"
    }
}

Write-Host "Enabling localhost access for Docker SQL..."
Start-Process -FilePath $dmgcmd -ArgumentList "-EnableLocalMachineAccess" -Verb RunAs -Wait | Out-Null

Write-Host "Restarting Integration Runtime service..."
Start-Process powershell -ArgumentList "-Command Restart-Service DIAHostService -Force" -Verb RunAs -Wait | Out-Null

Write-Host "Waiting for SHIR to come online..."
$deadline = (Get-Date).AddMinutes(5)
do {
    Start-Sleep -Seconds 15
    $statusJson = az datafactory integration-runtime get-status `
        --resource-group $ResourceGroup `
        --factory-name $FactoryName `
        --integration-runtime-name $IntegrationRuntimeName `
        -o json 2>$null | ConvertFrom-Json
    $state = $statusJson.properties.state
    $nodeStatus = $statusJson.properties.nodes[0].status
    $serviceBus = $statusJson.properties.nodes[0].capabilities.serviceBusConnected
    Write-Host "  IR state=$state node=$nodeStatus serviceBus=$serviceBus"
} while ($state -ne "Online" -and (Get-Date) -lt $deadline)

if ($state -ne "Online") {
    Write-Host ""
    Write-Host "WARN: SHIR registered but not Online yet."
    Write-Host "  1. Open ConfigManager.exe and confirm node is Running"
    Write-Host "  2. Check firewall allows outbound HTTPS to Azure"
    Write-Host "  3. Re-run: make azure-adf-publish"
    exit 1
}

Write-Host ""
Write-Host "SHIR setup initiated. Verify with:"
Write-Host "  powershell -ExecutionPolicy Bypass -File docker/azure/verify-adf.ps1"
