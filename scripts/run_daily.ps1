# QuantBIST - run the daily report by hand (the scheduled task calls
# pythonw.exe directly; see register_daily_task.ps1).
#   powershell -ExecutionPolicy Bypass -File scripts\run_daily.ps1
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& (Join-Path $root ".venv\Scripts\python.exe") -m core.reports.daily --send --log-dir logs
exit $LASTEXITCODE
