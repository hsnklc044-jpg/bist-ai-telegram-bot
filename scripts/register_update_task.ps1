# QuantBIST - register (or remove) the automatic updater in Windows Task Scheduler.
#
#   powershell -ExecutionPolicy Bypass -File scripts\register_update_task.ps1           # create / update
#   powershell -ExecutionPolicy Bypass -File scripts\register_update_task.ps1 -Remove   # delete
#
# Every day from 07:40, once an hour for 16 hours, the task runs scripts\guncelle.py from THIS
# folder: it installs the newest version whose CI passed (backup, tests in a staging copy, bot
# restart, rollback if the bot does not come up). Nothing new: nothing happens, no message.
# 18:00-20:00 it waits (the daily report). Replaces the older task that pointed to C:\Projeler\QuantBIST.

param([switch]$Remove, [string]$Time = "07:40")

$name = "QuantBIST Guncelle"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
    Write-Host "Silindi: $name"
    exit 0
}

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$script = Join-Path $root "scripts\guncelle.py"
if (-not (Test-Path $python)) {
    Write-Host "Bulunamadi: $python - once scripts\setup.ps1 ile kurulum yapin."
    exit 1
}

$action = New-ScheduledTaskAction -Execute $python -Argument "`"$script`"" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At $Time `
    -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Hours 16)).Repetition
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 50) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings `
    -Description "QuantBIST: CI'i yesil yeni surumu kur (git), testle, botu yeniden baslat" -Force | Out-Null

Write-Host "Kuruldu: '$name' - her gun $Time'dan itibaren saatte bir (16 saat)"
Write-Host "Klasor: $root"
Write-Host "Hemen denemek icin:  Start-ScheduledTask -TaskName '$name'"
