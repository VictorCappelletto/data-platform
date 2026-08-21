# Build and push olist-transform image to ACR (after infra deploy).
param(
    [string]$EnvFile = ".env",
    [string]$ImageTag = "latest"
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

$acrLogin = Get-EnvValue "AZURE_ACR_LOGIN_SERVER"
if ([string]::IsNullOrWhiteSpace($acrLogin)) {
    $acrName = Get-EnvValue "AZURE_ACR_NAME"
    if (-not [string]::IsNullOrWhiteSpace($acrName)) {
        $acrLogin = "$acrName.azurecr.io"
    }
}
if ([string]::IsNullOrWhiteSpace($acrLogin)) {
    throw "AZURE_ACR_LOGIN_SERVER not set. Run: make azure-infra-deploy"
}

$imageName = Get-EnvValue "AZURE_TRANSFORM_IMAGE"
if ([string]::IsNullOrWhiteSpace($imageName)) {
    $imageName = "olist-transform"
}

$fullImage = "$acrLogin/${imageName}:$ImageTag"
$dockerfile = Join-Path $repo "docker\ingestion_azure\Dockerfile"

Write-Host "Building $fullImage ..."
docker build -f $dockerfile -t $fullImage $repo
if ($LASTEXITCODE -ne 0) { throw "docker build failed" }

Write-Host "Logging in to ACR $acrLogin ..."
az acr login --name ($acrLogin -replace '\.azurecr\.io$', '')
if ($LASTEXITCODE -ne 0) { throw "acr login failed" }

Write-Host "Pushing $fullImage ..."
docker push $fullImage
if ($LASTEXITCODE -ne 0) { throw "docker push failed" }

Write-Host "Image pushed: $fullImage"
Write-Host "Next: make azure-adf-publish && make azure-olist-full"
