# Push OIDC values to GitHub Actions secrets (requires: gh auth login).
param(
    [string]$OidcFile = "config/azure/oidc.generated.env",
    [string]$Repo = "VictorCappelletto/data-platform"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $OidcFile)) {
    throw "Missing $OidcFile — run: docker compose --profile azure run --rm azure setup"
}

$values = @{}
Get-Content $OidcFile | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)=(.*)$' -and $_ -notmatch '^\s*#') {
        $values[$Matches[1]] = $Matches[2]
    }
}

$required = @("AZURE_CLIENT_ID", "AZURE_TENANT_ID", "AZURE_SUBSCRIPTION_ID")
foreach ($key in $required) {
    if (-not $values.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($values[$key])) {
        throw "Missing $key in $OidcFile"
    }
}

gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "GitHub CLI not authenticated. Run: gh auth login"
}

Write-Host "Setting GitHub Actions secrets on $Repo ..."
foreach ($key in $required) {
    gh secret set $key --body $values[$key] --repo $Repo
    Write-Host "  set $key"
}

Write-Host "Done. Trigger workflow: gh workflow run azure-infra --repo $Repo"
