# Run this script as Administrator to repair Self-hosted IR connectivity.
#Requires -RunAsAdministrator
param(
    [string]$ResourceGroup = "rg-olist-dev",
    [string]$FactoryName = "",
    [string]$IntegrationRuntimeName = "shir-olist-dev",
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"
$dmgcmd = "C:\Program Files\Microsoft Integration Runtime\5.0\Shared\dmgcmd.exe"

function Get-EnvValue {
    param([string]$Key)
    if (Test-Path $EnvFile) {
        foreach ($line in Get-Content $EnvFile) {
            if ($line -match "^\s*$Key=(.*)$") { return $Matches[1].Trim() }
        }
    }
    return (Get-Item -Path "Env:$Key" -ErrorAction SilentlyContinue).Value
}

if ([string]::IsNullOrWhiteSpace($FactoryName)) {
    $FactoryName = Get-EnvValue "AZURE_DATA_FACTORY_NAME"
}

Write-Host "Repairing SHIR on $FactoryName..."

Write-Host "Syncing system clock (fixes AuthSasEffectiveInFuture)..."
Set-Service W32Time -StartupType Automatic -ErrorAction SilentlyContinue
Start-Service W32Time -ErrorAction SilentlyContinue
w32tm /config /manualpeerlist:"time.windows.com,0x9" /syncfromflags:manual /reliable:YES /update 2>$null | Out-Null
w32tm /resync /force 2>$null | Out-Null
Write-Host "  Local time: $(Get-Date -Format o)"

if (Test-Path $dmgcmd) {
    & $dmgcmd -EnableLocalMachineAccess
    Write-Host "  Enabled localhost access"
}

Restart-Service DIAHostService -Force
Write-Host "  Restarted DIAHostService"

Start-Sleep -Seconds 20
$status = az datafactory integration-runtime get-status `
    --resource-group $ResourceGroup `
    --factory-name $FactoryName `
    --integration-runtime-name $IntegrationRuntimeName `
    --query "{state:properties.state, node:properties.nodes[0].status, sb:properties.nodes[0].capabilities.serviceBusConnected}" `
    -o json | ConvertFrom-Json

Write-Host "  State: $($status.state) | Node: $($status.node) | ServiceBus: $($status.sb)"

if ($status.state -eq "Online") {
    Write-Host ""
    Write-Host "SHIR is Online. Run:"
    Write-Host "  make azure-adf-publish"
    Write-Host "  make azure-adf-trigger"
} else {
    Write-Host ""
    Write-Host "Still offline. Open ConfigManager.exe and check:"
    Write-Host "  - Node status should be Running"
    Write-Host "  - Firewall allows outbound HTTPS (443) to Azure"
    Write-Host "  - No corporate proxy blocking Service Bus"
}
