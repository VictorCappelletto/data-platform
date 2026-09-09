# Deploy subscription infra (storage + ADF + Azure SQL) with password from .env

param(

    [string]$EnvFile = ".env",

    [string]$DeploymentName = "local-olist-infra"

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



$password = Get-EnvValue "MSSQL_SA_PASSWORD"

if ([string]::IsNullOrWhiteSpace($password)) {

    $password = Get-EnvValue "AZURE_SQL_ADMIN_PASSWORD"

}

if ([string]::IsNullOrWhiteSpace($password)) {

    throw "MSSQL_SA_PASSWORD or AZURE_SQL_ADMIN_PASSWORD required in $EnvFile"

}



$paramTemplate = Join-Path $PSScriptRoot "..\..\infra\parameters\dev.deploy.json"

$paramFile = Join-Path $env:TEMP ("bicep-params-" + [guid]::NewGuid().ToString() + ".json")

(Get-Content $paramTemplate -Raw).Replace("__SQL_ADMIN_PASSWORD__", ($password -replace '\\', '\\\\' -replace '"', '\"')) |

    Set-Content $paramFile -Encoding utf8



try {
    Write-Host "What-if infra/main.bicep ..."
    az deployment sub what-if `
        --location eastus `
        --template-file infra/main.bicep `
        --parameters "@$paramFile"
    if ($LASTEXITCODE -ne 0) { throw "Bicep what-if failed" }

    Write-Host "Deploying infra/main.bicep ..."
    az deployment sub create `
        --location eastus `
        --template-file infra/main.bicep `
        --parameters "@$paramFile" `
        --name $DeploymentName
    if ($LASTEXITCODE -ne 0) { throw "Bicep deploy failed" }
} finally {

    Remove-Item $paramFile -Force -ErrorAction SilentlyContinue

}



powershell -ExecutionPolicy Bypass -File docker/azure/sync-deploy-outputs.ps1 -DeploymentName $DeploymentName



Write-Host "Infra deploy complete."

