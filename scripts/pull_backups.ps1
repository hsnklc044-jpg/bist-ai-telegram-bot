# QuantBIST - copy the server's backups to this PC and check them (Windows PowerShell)
#
#   powershell -ExecutionPolicy Bypass -File scripts\pull_backups.ps1 -Server kullanici@sunucu
#   optional: -Remote QuantBIST/backups  -Local "$env:USERPROFILE\OneDrive\QuantBIST-sunucu-yedek"
#
# 1. scp (built into Windows 10/11) copies every quantbist_*.zip from the server
# 2. python -m core.backup --test-restore opens the newest ones in a temporary
#    folder and reads every file; live files are not touched
# 3. only if that passed: pulled.txt is written on the server, so /durum there
#    knows a separate copy exists
# Run it weekly, e.g. as a Windows scheduled task; /durum on the server warns
# after 8 days without a pull.

param(
    [Parameter(Mandatory = $true)][string]$Server,
    [string]$Remote = "QuantBIST/backups",
    [string]$Local = (Join-Path $env:USERPROFILE "OneDrive\QuantBIST-sunucu-yedek")
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
New-Item -ItemType Directory -Force -Path $Local | Out-Null

Write-Host "Sunucudan aliniyor: ${Server}:$Remote -> $Local"
& scp -q "${Server}:$Remote/quantbist_*.zip" "$Local\"
if ($LASTEXITCODE -ne 0) { Write-Host "HATA: scp basarisiz ($LASTEXITCODE)"; exit 1 }

Write-Host "Kontrol ediliyor (gecici klasorde; canli dosyalara dokunulmaz) ..."
$env:BACKUP_DIR = $Local
Push-Location $root
& $python -m core.backup --test-restore
$ok = $LASTEXITCODE -eq 0
Pop-Location
if (-not $ok) { Write-Host "HATA: yedekler okunamadi; sunucuya pulled.txt yazilmadi"; exit 1 }

& ssh $Server "date -Iseconds > '$Remote/pulled.txt'"
if ($LASTEXITCODE -ne 0) { Write-Host "HATA: sunucuya pulled.txt yazilamadi"; exit 1 }
Write-Host "Tamam: yedekler $Local icinde; sunucuya pulled.txt yazildi."
