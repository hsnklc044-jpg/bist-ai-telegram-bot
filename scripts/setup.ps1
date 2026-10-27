# QuantBIST - reproducible setup and check (Windows PowerShell)
#
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1            # install + check
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -CheckOnly # check only
#
# Creates .venv with Python 3.11, installs the exact versions from
# requirements.lock, runs ruff and the tests, and writes everything to
# logs\setup_report.txt so the result can be shared as proof.

param([switch]$CheckOnly)

# Windows PowerShell 5.1 turns any stderr line of a native program (git, pip, pytest) into a
# terminating error under "Stop"; native results are judged by their exit codes instead.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
New-Item -ItemType Directory -Force -Path logs | Out-Null
$report = Join-Path $root "logs\setup_report.txt"
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not $CheckOnly) {
    if (-not (Test-Path $python)) {
        Write-Host "Creating .venv with Python 3.11 ..."
        py -3.11 -m venv .venv
        if ($LASTEXITCODE -ne 0) { Write-Host "Python 3.11 venv could not be created"; exit 1 }
    }
    & $python -m pip install --upgrade pip --quiet
    if ($LASTEXITCODE -ne 0) { Write-Host "pip upgrade failed"; exit 1 }
    & $python -m pip install -r requirements.lock --quiet
    if ($LASTEXITCODE -ne 0) { Write-Host "package install failed"; exit 1 }
}

$version = & $python --version
$release = & $python -c "import core; print(core.__version__)"
# releases are delivered as zips without git history; a commit shown here comes
# from a local git folder and may not match the files
$commit = $null
if (Test-Path (Join-Path $root ".git")) { $commit = (git rev-parse --short HEAD 2>$null) }
if (-not $commit) { $commit = "(no git)" }

$frozen = & $python -m pip freeze
$locked = Get-Content requirements.lock | Where-Object { $_ -and -not $_.StartsWith("#") }
$diff = Compare-Object $locked $frozen | ForEach-Object { "$($_.SideIndicator) $($_.InputObject)" }

Write-Host "Running ruff ..."
$ruff = & $python -m ruff check . 2>&1
$ruffOk = $LASTEXITCODE -eq 0

Write-Host "Running tests ..."
$tests = & $python -m pytest -q 2>&1
$testsOk = $LASTEXITCODE -eq 0

$lines = @(
    "QuantBIST setup report",
    "date:     $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "quantbist: v$release",
    "local git: $commit (zip releases carry no git history)",
    "python:   $version",
    "packages: $(if ($diff) { 'DIFFERENT from requirements.lock' } else { 'identical to requirements.lock' })"
)
if ($diff) { $lines += $diff }
$lines += ""
$lines += "ruff:     $(if ($ruffOk) { 'OK' } else { 'FAILED' })"
$lines += $ruff
$lines += ""
$lines += "tests:    $(if ($testsOk) { 'OK' } else { 'FAILED' })"
$lines += ($tests | Select-Object -Last 15)

$lines | Set-Content -Encoding UTF8 $report
$lines | ForEach-Object { Write-Host $_ }
Write-Host ""
Write-Host "Report written to $report"

if (-not ($ruffOk -and $testsOk)) { exit 1 }
