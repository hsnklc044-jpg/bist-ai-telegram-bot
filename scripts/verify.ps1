# QuantBIST - installation proof in one file (Windows PowerShell)
#
#   powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
#
# 1. setup.ps1 -CheckOnly: version, package lock, ruff, tests
# 2. core.reports.verify: /durum checks, price store snapshot and restore
#    test (temporary folder; live files are not touched), last report runs,
#    end of the newest daily log
# Everything goes to logs\verify_report.txt with the bot token and the chat
# id replaced, so the file can be pasted into the chat as it is.
# Stop the bot first only if you want the restore test to run without it;
# the snapshot is consistent while the bot runs.

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
New-Item -ItemType Directory -Force -Path logs | Out-Null
$python = Join-Path $root ".venv\Scripts\python.exe"
$out = Join-Path $root "logs\verify_report.txt"
$part = Join-Path $root "logs\verify_part.txt"

& powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "setup.ps1") -CheckOnly | Out-Null
$setupOk = $LASTEXITCODE -eq 0

& $python -m core.reports.verify --out $part | Out-Null
$verifyOk = $LASTEXITCODE -eq 0

$lines = @("== setup.ps1 -CheckOnly ($(if ($setupOk) { 'OK' } else { 'FAILED' })) ==")
$lines += Get-Content -Encoding UTF8 (Join-Path $root "logs\setup_report.txt")
$lines += ""
$lines += Get-Content -Encoding UTF8 $part
$lines | Set-Content -Encoding UTF8 $out
Remove-Item $part -ErrorAction SilentlyContinue

$lines | ForEach-Object { Write-Host $_ }
Write-Host ""
Write-Host "Hepsi tek dosyada: $out (token ve chat id gizlendi; sohbete yapistirabilirsiniz)"
if (-not ($setupOk -and $verifyOk)) { exit 1 }
