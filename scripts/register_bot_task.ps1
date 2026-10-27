# QuantBIST - start the Telegram bot at logon with Windows Task Scheduler (or remove it).
#
#   powershell -ExecutionPolicy Bypass -File scripts\register_bot_task.ps1           # create / update
#   powershell -ExecutionPolicy Bypass -File scripts\register_bot_task.ps1 -Remove   # delete
#
# At logon the task runs .venv\Scripts\pythonw.exe main.py (no console window).
# If the bot stops it is started again after 5 minutes (at most 3 times), and a
# second copy is never started while one runs: Telegram refuses two bots with the
# same token (seen on 27.10.2026). Do not also start "python main.py" by hand.
# Runs for the current user while logged on (no password is stored); battery
# power does not block or stop it. The daily report has its own task
# (scripts\register_daily_task.ps1); keep DAILY_REPORT_AT empty on the PC.

param([switch]$Remove)

$name = "QuantBIST Bot"

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

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "main.py" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit 0 -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings `
    -Description "QuantBIST: Telegram botu (oturum acilisinda, tek kopya)" -Force | Out-Null

Write-Host "Kuruldu: '$name' - oturum acilisinda baslar"
Write-Host "Calistirilan: $pythonw main.py"
Write-Host "Hemen baslatmak icin once calisan botu kapatin, sonra:  Start-ScheduledTask -TaskName '$name'"
