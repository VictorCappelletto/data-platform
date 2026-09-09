# Fix AuthSasEffectiveInFuture — sync clock and restart SHIR. Requires Administrator.
#Requires -RunAsAdministrator
param(
    [string]$ResourceGroup = "rg-olist-dev",
    [string]$FactoryName = "adf-olisthfh5ri63",
    [string]$IntegrationRuntimeName = "shir-olist-dev",
    [string]$NodeName = "olist-dev-node"
)

$ErrorActionPreference = "Stop"
$dmgcmd = "C:\Program Files\Microsoft Integration Runtime\5.0\Shared\dmgcmd.exe"

Write-Host "=== Fix SHIR clock skew (AuthSasEffectiveInFuture) ==="
Write-Host "Local time: $(Get-Date -Format o)"

Write-Host "Starting Windows Time service..."
Set-Service W32Time -StartupType Automatic -ErrorAction SilentlyContinue
Start-Service W32Time -ErrorAction SilentlyContinue
w32tm /config /manualpeerlist:"time.windows.com,0x9" /syncfromflags:manual /reliable:YES /update | Out-Null
w32tm /resync /force

Start-Sleep -Seconds 5
Write-Host "Time after sync: $(Get-Date -Format o)"

Write-Host "Restarting Integration Runtime..."
& $dmgcmd -EnableLocalMachineAccess | Out-Null
Restart-Service DIAHostService -Force
Start-Sleep -Seconds 20

$deadline = (Get-Date).AddMinutes(3)
do {
    $status = az datafactory integration-runtime get-status `
        --resource-group $ResourceGroup `
        --factory-name $FactoryName `
        --integration-runtime-name $IntegrationRuntimeName `
        -o json | ConvertFrom-Json
    $state = $status.properties.state
    $sb = $status.properties.nodes[0].capabilities.serviceBusConnected
    Write-Host "  state=$state serviceBus=$sb"
    if ($state -eq "Online") { break }
    Start-Sleep -Seconds 15
} while ((Get-Date) -lt $deadline)

if ($state -ne "Online") {
    Write-Host "Still offline after time sync. Re-registering node..."
    $key = (az datafactory integration-runtime list-auth-key `
        --resource-group $ResourceGroup `
        --factory-name $FactoryName `
        --integration-runtime-name $IntegrationRuntimeName `
        -o json | ConvertFrom-Json).authKey1
    & $dmgcmd -RegisterNewNode $key $NodeName
    Restart-Service DIAHostService -Force
    Start-Sleep -Seconds 30
    $state = az datafactory integration-runtime get-status `
        --resource-group $ResourceGroup `
        --factory-name $FactoryName `
        --integration-runtime-name $IntegrationRuntimeName `
        --query "properties.state" -o tsv
}

if ($state -eq "Online") {
    Write-Host ""
    Write-Host "SHIR Online!"
    exit 0
}

Write-Host ""
Write-Host "Check event log: Get-WinEvent -LogName 'Integration Runtime' -MaxEvents 5"
exit 1
