#!/usr/bin/env bash
# QuantBIST - copy the server's backups to this computer and check them (Linux/macOS).
# Windows: scripts\pull_backups.ps1. Run it on the computer that keeps the copy, not on the server.
#
#   scripts/pull_backups.sh user@server [remote folder] [local folder]
#   defaults: ~/QuantBIST/backups on the server, ~/QuantBIST-sunucu-yedek here
#
# 1. scp every quantbist_*.zip from the server
# 2. open the newest ones in a temporary folder and read every file
#    (python -m core.backup --test-restore with BACKUP_DIR set to the copy)
# 3. only if that passed: write pulled.txt on the server, so /durum there
#    knows a separate copy exists (core/reports/health.py, PULL_MARKER)
set -euo pipefail

server="${1:?kullanım: scripts/pull_backups.sh kullanici@sunucu [uzak klasör] [yerel klasör]}"
remote="${2:-QuantBIST/backups}"
local_dir="${3:-$HOME/QuantBIST-sunucu-yedek}"
here="$(cd "$(dirname "$0")/.." && pwd)"
python="${PYTHON:-$here/.venv/bin/python}"
[ -x "$python" ] || python="python3"

mkdir -p "$local_dir"
echo "Sunucudan alınıyor: $server:$remote → $local_dir"
${SCP:-scp} -q "$server:$remote/quantbist_*.zip" "$local_dir/"

echo "Kontrol ediliyor (geçici klasörde; canlı dosyalara dokunulmaz) ..."
(cd "$here" && BACKUP_DIR="$local_dir" "$python" -m core.backup --test-restore --no-record)

${SSH:-ssh} "$server" "date -Iseconds > '$remote/pulled.txt'"
echo "Tamam: $(ls "$local_dir"/quantbist_*.zip | wc -l) yedek $local_dir içinde; sunucuya pulled.txt yazıldı."
