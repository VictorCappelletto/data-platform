# Run diagnostics and re-register SHIR if offline. Requires Administrator.
#Requires -RunAsAdministrator
param(
    [string]$ResourceGroup = "rg-olist-dev",
    [string]$FactoryName = "adf-olisthfh5ri63",
    [string]$IntegrationRuntimeName = "shir-olist-dev",
    [string]$NodeName = "olist-dev-node",
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"
$dmgcmd = "C:\Program Files\Microsoft Integration Runtime\5.0\Shared\dmgcmd.exe"
$reportDir = Join-Path $env:TEMP "shir-diagnostics"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

function Get-EnvValue {
    param([string]$Key)
    if (Test-Path $EnvFile) {
        foreach ($line in Get-Content $EnvFile) {
            if ($line -match "^\s*$Key=(.*)$") { return $Matches[1].Trim() }
        }
    }
    return (Get-Item -Path "Env:$Key" -ErrorAction SilentlyContinue).Value
}

if (-not (Test-Path $dmgcmd)) {
    throw "Integration Runtime not installed. Run: make azure-shir-setup"
}

if ([string]::IsNullOrWhiteSpace($FactoryName)) {
    $FactoryName = Get-EnvValue "AZURE_DATA_FACTORY_NAME"
}

Write-Host "=== SHIR diagnostics ($FactoryName) ==="

$keyJson = az datafactory integration-runtime list-auth-key `
    --resource-group $ResourceGroup `
    --factory-name $FactoryName `
    --integration-runtime-name $IntegrationRuntimeName `
    -o json | ConvertFrom-Json
$key = $keyJson.authKey1

Write-Host "Running dmgcmd troubleshoot (report in $reportDir)..."
Push-Location $reportDir
& $dmgcmd -ts $key 2>&1 | Out-File (Join-Path $reportDir "troubleshoot-console.txt")
Pop-Location

$htmlReport = Get-ChildItem $reportDir -Filter "*.html" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($htmlReport) {
    Write-Host "  Diagnostic report: $($htmlReport.FullName)"
}

$status = az datafactory integration-runtime get-status `
    --resource-group $ResourceGroup `
    --factory-name $FactoryName `
    --integration-runtime-name $IntegrationRuntimeName `
    -o json | ConvertFrom-Json

$state = $status.properties.state
Write-Host "  Current state: $state"

if ($state -ne "Online") {
    Write-Host "Re-registering node with fresh auth key..."
    az datafactory integration-runtime regenerate-auth-key `
        --resource-group $ResourceGroup `
        --factory-name $FactoryName `
        --integration-runtime-name $IntegrationRuntimeName `
        --key-name authKey1 `
        --only-show-errors | Out-Null

    $keyJson = az datafactory integration-runtime list-auth-key `
        --resource-group $ResourceGroup `
        --factory-name $FactoryName `
        --integration-runtime-name $IntegrationRuntimeName `
        -o json | ConvertFrom-Json
    $key = $keyJson.authKey1

    & $dmgcmd -EnableLocalMachineAccess | Out-Null
    $proc = Start-Process -FilePath $dmgcmd -ArgumentList "-RegisterNewNode `"$key`" $NodeName" -Wait -PassThru -NoNewWindow
    if ($proc.ExitCode -ne 0) {
        Write-Host "  Register exit code: $($proc.ExitCode)"
    }
    Restart-Service DIAHostService -Force
}

Write-Host "Waiting for Online state (up to 3 min)..."
$deadline = (Get-Date).AddMinutes(3)
do {
    Start-Sleep -Seconds 15
    $status = az datafactory integration-runtime get-status `
        --resource-group $ResourceGroup `
        --factory-name $FactoryName `
        --integration-runtime-name $IntegrationRuntimeName `
        -o json | ConvertFrom-Json
    $state = $status.properties.state
    $node = $status.properties.nodes[0].status
    $sb = $status.properties.nodes[0].capabilities.serviceBusConnected
    Write-Host "  state=$state node=$node serviceBus=$sb"
} while ($state -ne "Online" -and (Get-Date) -lt $deadline)

if ($state -eq "Online") {
    Write-Host ""
    Write-Host "SHIR Online. Next:"
    Write-Host "  make azure-adf-publish"
    Write-Host "  make azure-adf-trigger"
    exit 0
}

Write-Host ""
Write-Host "Still offline. Open diagnostic HTML report and ConfigManager.exe:"
Write-Host "  $reportDir"
Write-Host "  C:\Program Files\Microsoft Integration Runtime\5.0\Shared\ConfigManager.exe"
exit 1
