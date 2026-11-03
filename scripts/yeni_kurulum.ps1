# QuantBIST - clean install next to an old folder (Windows PowerShell 5.1+)
#
#   powershell -ExecutionPolicy Bypass -File yeni_kurulum.ps1
#   powershell -ExecutionPolicy Bypass -File yeni_kurulum.ps1 -Old C:\Projeler\QuantBIST -New C:\Projeler\QuantBIST-yeni
#
# 1. Clones the current release into a NEW folder (stops if that folder exists: nothing is overwritten).
# 2. Copies .env and the personal files of data\ that the release does not have (watchlist, ledger,
#    paper orders, market.db ...): files already in the release are never replaced by old copies.
# 3. Runs scripts\setup.ps1 there (Python 3.11 venv, exact packages, ruff, tests).
# The old folder is only read: nothing in it is changed, stopped or deleted.
# Messages are ASCII on purpose: Windows PowerShell 5.1 misreads UTF-8 scripts without a BOM.

param(
    [string]$Old = "C:\Projeler\QuantBIST",
    [string]$New = "C:\Projeler\QuantBIST-yeni",
    [string]$Branch = "claude/borsa-bot-creation-n7nmc9",
    [string]$Repo = "https://github.com/hsnklc044-jpg/bist-ai-telegram-bot.git"
)

$ErrorActionPreference = "Continue"

function Fail($message) {
    Write-Host "HATA: $message" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "git bulunamadi (https://git-scm.com)." }
& py -3.11 --version *> $null
if ($LASTEXITCODE -ne 0) { Fail "Python 3.11 bulunamadi (py -3.11)." }
if (Test-Path $New) { Fail "$New zaten var. Ustune yazilmaz; baska bir -New klasoru verin." }

Write-Host "1/3 Guncel surum indiriliyor: $Branch"
& git clone --quiet --branch $Branch $Repo $New
if ($LASTEXITCODE -ne 0) { Fail "git clone basarisiz (internet ya da GitHub erisimi)." }

Write-Host "2/3 Kisisel dosyalar kopyalaniyor (eski klasor degismez)"
if (Test-Path (Join-Path $Old ".env")) {
    Copy-Item (Join-Path $Old ".env") (Join-Path $New ".env")
    Write-Host "    .env kopyalandi"
} else {
    Write-Host "    UYARI: $Old\.env yok; .env.example'dan .env olusturup token'i siz yazin." -ForegroundColor Yellow
}
if (Test-Path (Join-Path $Old "data")) {
    # /XC /XN /XO: copy only files the release does not have; never replace a release file
    & robocopy (Join-Path $Old "data") (Join-Path $New "data") /E /XC /XN /XO /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { Fail "data klasoru kopyalanamadi (robocopy $LASTEXITCODE)." }
    Write-Host "    data\ icindeki kisisel dosyalar kopyalandi"
}

Write-Host "3/3 Kurulum ve testler (birkac dakika surer)"
& powershell -ExecutionPolicy Bypass -File (Join-Path $New "scripts\setup.ps1")
if ($LASTEXITCODE -ne 0) { Fail "Kurulum ya da testler basarisiz; rapor: $New\logs\setup_report.txt" }

Write-Host ""
Write-Host "Tamam. Yeni surum: $New" -ForegroundColor Green
Write-Host "Simdi: eski botu durdurun (ayni anda iki bot calisamaz), sonra:"
Write-Host "    cd $New"
Write-Host "    .\.venv\Scripts\python.exe main.py"
Write-Host "Eski klasor ($Old) yedek olarak duruyor; silmek sizin kararinizdir."
