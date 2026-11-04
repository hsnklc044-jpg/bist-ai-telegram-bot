# QuantBIST - measurement check on this PC (K-76), one command instead of a chat session
#
#   powershell -ExecutionPolicy Bypass -File scripts\olcum.ps1
#
# 1. downloads the BIST 30 hourly candles (the same Yahoo data the bot already uses) and freezes the
#    part before the holdout (02.11.2026) into <BACKUP_DIR>\olcum\ (OneDrive when BACKUP_DIR points there)
# 2. runs K-63 and K-64 hourly twice on that frozen data and checks that both runs are identical
# 3. freezes the local daily price store (before the holdout) next to it
# The short result goes to logs\olcum_report.txt: paste that file into the chat. No rule, threshold
# or record of the bot is changed; it is a repeatability check, not a decision measurement.

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$python = Join-Path $root ".venv\Scripts\python.exe"
& $python -m core.analytics.provenance pc
$code = $LASTEXITCODE
Write-Host ""
Write-Host "Rapor: $(Join-Path $root 'logs\olcum_report.txt')"
exit $code
