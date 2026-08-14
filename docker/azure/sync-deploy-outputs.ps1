# After deploy — capture outputs and merge into .env (non-secret infra vars).
param(
    [string]$DeploymentName = "",
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($DeploymentName)) {
    $DeploymentName = az deployment sub list --query "max_by([], &properties.timestamp).name" -o tsv 2>$null
}

if ([string]::IsNullOrWhiteSpace($DeploymentName)) {
    throw "No subscription deployment found. Run: az deployment sub create ..."
}

Write-Host "Reading deployment outputs: $DeploymentName"
$outputs = az deployment sub show --name $DeploymentName --query properties.outputs -o json | ConvertFrom-Json

$vars = @{
    AZURE_STORAGE_ACCOUNT   = $outputs.storageAccountName.value
    AZURE_ADLS_ENDPOINT     = $outputs.adlsEndpoint.value
    AZURE_DATA_FACTORY_NAME = $outputs.dataFactoryName.value
}

if (-not (Test-Path $EnvFile)) {
    Copy-Item ".env.example" $EnvFile
}

$content = if (Test-Path $EnvFile) { Get-Content $EnvFile -Raw } else { "" }
foreach ($key in $vars.Keys) {
    $value = $vars[$key]
    if ($content -match "(?m)^$key=.*") {
        $content = $content -replace "(?m)^$key=.*", "$key=$value"
    } else {
        $content += "`n$key=$value"
    }
}
Set-Content -Path $EnvFile -Value $content.TrimEnd() -Encoding utf8

Write-Host "Updated ${EnvFile}:"
foreach ($key in $vars.Keys) {
    Write-Host "  $key=$($vars[$key])"
}
