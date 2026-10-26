# QuantBIST - register (or remove) the daily report in Windows Task Scheduler.
#
#   powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1           # create / update
#   powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1 -Remove   # delete
#
# Every weekday at 18:30 the task runs .venv\Scripts\pythonw.exe directly
# (no PowerShell in between, no console window). The run writes
# logs\daily_<date>.log itself: the report, or the full error.
# Runs for the current user while logged on (no password is stored);
# if the computer was off at 18:30 it runs as soon as possible afterwards.
# Battery power does not block it (Windows blocks tasks on battery by default).

param([switch]$Remove, [string]$Time = "18:30")

$name = "QuantBIST Gunluk Rapor"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
    Write-Host "Silindi: $name"
    exit 0
}

$root = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonw)) {
    Write-Host "Bulunamadi: $pythonw - once scripts\setup.ps1 ile kurulum yapin."
    exit 1
}

$action = New-ScheduledTaskAction -Execute $pythonw `
    -Argument "-m core.reports.daily --send --log-dir logs" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings `
    -Description "QuantBIST: fiyat guncelle, sanal emirleri doldur, risk uyarilari, Telegram raporu" -Force | Out-Null

Write-Host "Kuruldu: '$name' - hafta ici her gun $Time"
Write-Host "Calistirilan: $pythonw -m core.reports.daily --send --log-dir logs"
Write-Host "Hemen denemek icin:  Start-ScheduledTask -TaskName '$name'"
