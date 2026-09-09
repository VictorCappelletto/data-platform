# Trigger ADF pipeline and wait for completion.
param(
    [string]$ResourceGroup = "rg-olist-dev",
    [string]$FactoryName = "",
    [string]$PipelineName = "pl_olist_end_to_end",
    [string]$EnvFile = ".env",
    [int]$TimeoutMinutes = 45
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

Write-Host "Starting pipeline run: $PipelineName on $FactoryName"
$runId = az datafactory pipeline create-run `
    --resource-group $ResourceGroup `
    --factory-name $FactoryName `
    --name $PipelineName `
    --query runId -o tsv

Write-Host "  Run ID: $runId"
Write-Host "  Monitor: https://adf.azure.com/en/authoring/pipeline/$PipelineName?factory=$FactoryName"

$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
do {
    Start-Sleep -Seconds 15
    $status = az datafactory pipeline-run show `
        --resource-group $ResourceGroup `
        --factory-name $FactoryName `
        --run-id $runId `
        --query status -o tsv
    Write-Host "  Status: $status"
} while ($status -in @("Queued", "InProgress") -and (Get-Date) -lt $deadline)

if ($status -ne "Succeeded") {
    throw "Pipeline run $runId ended with status: $status"
}

Write-Host ""
Write-Host "Pipeline $PipelineName succeeded."
