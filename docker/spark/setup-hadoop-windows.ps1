# One-time setup: Hadoop winutils for PySpark writes on Windows.
param(
    [string]$RepoRoot = "",
    [string]$HadoopVersion = "3.3.6"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
    if (-not (Test-Path (Join-Path $RepoRoot "pyproject.toml"))) {
        $RepoRoot = (Split-Path $PSScriptRoot -Parent) | Split-Path -Parent
    }
}

$HadoopHome = Join-Path $RepoRoot "docker\spark\hadoop"
$BinDir = Join-Path $HadoopHome "bin"
$Winutils = Join-Path $BinDir "winutils.exe"
$HadoopDll = Join-Path $BinDir "hadoop.dll"
$BaseUrl = "https://raw.githubusercontent.com/cdarlint/winutils/master/hadoop-$HadoopVersion/bin"

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

function Download-Binary {
    param([string]$Name, [string]$Dest)
    if (Test-Path $Dest) { return }
    $url = "$BaseUrl/$Name"
    Write-Host "Downloading $Name..."
    try {
        Invoke-WebRequest -Uri $url -OutFile $Dest -UseBasicParsing
    } catch {
        Write-Host "Invoke-WebRequest failed, trying curl..."
        curl.exe -fsSL -o $Dest $url
    }
}

Download-Binary "winutils.exe" $Winutils
Download-Binary "hadoop.dll" $HadoopDll

if (-not (Test-Path $Winutils)) {
    throw "Failed to download winutils.exe to $Winutils"
}

$size = (Get-Item $Winutils).Length
if ($size -lt 10000) {
    throw "winutils.exe looks invalid (size=$size). Delete and retry."
}

# Best-effort chmod on Spark staging dir (full TEMP often fails on Windows)
$SparkLake = Join-Path $env:TEMP "data-platform-spark-lake"
New-Item -ItemType Directory -Force -Path $SparkLake | Out-Null
& $Winutils chmod -R 777 $SparkLake 2>$null | Out-Null

Write-Host ""
Write-Host "Hadoop Windows setup OK"
Write-Host "  HADOOP_HOME=$HadoopHome"
Write-Host "  winutils=$Winutils ($size bytes)"
Write-Host ""
Write-Host "For current session:"
Write-Host ('  $env:HADOOP_HOME = "' + $HadoopHome + '"')
Write-Host ""
Write-Host "Optional - persist for your user:"
Write-Host ('  [Environment]::SetEnvironmentVariable("HADOOP_HOME", "' + $HadoopHome + '", "User")')
