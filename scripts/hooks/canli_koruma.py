"""QuantBIST PreToolUse hook (kullanıcı onayı 17.11, yönlendirme madde 5).

Engeller:
  1. Write/Edit/NotebookEdit ile canlı kurulum klasörüne (C:\\Projeler\\QuantBIST-yeni\\) yazma.
     Canlıya her şey dal + surum-kapisi + güncelleyici yoluyla gider (CLAUDE.md, K-54).
  2. Bash/PowerShell ile git geçmişini yeniden yazma (push --force, reset --hard, rebase, filter-branch).
  3. Bash/PowerShell ile canlı klasöre doğrudan dosya yazma (yönlendirme ya da yazan cmdlet).

Okuma ve canlı klasördeki git okuma komutları (log, status, rev-parse, fetch) serbesttir.
Karar JSON olarak stdout'a yazılır; hata olursa sessizce izin verir (hook kendisi sistemi kilitlemesin).
"""
from __future__ import annotations

import json
import re
import sys

LIVE = r"(?:c:|/c)[\\/]+projeler[\\/]+quantbist-yeni(?=[\\/\"' ;&|)]|$)"

# "git" + isteğe bağlı -C/-c seçenekleri + alt komut (commit mesajındaki kelimeler eşleşmesin)
# git komut başında olmalı (satır başı ya da ; & | ( sonrası): tırnak içindeki metin (rapor satırı) eşleşmesin
GIT = r"(?:^|[;&|(]|\n)\s*(?:&\s*)?git(?:\.exe)?(?:\s+-[Cc]\s+(?:\"[^\"]*\"|'[^']*'|\S+))*\s+"
GIT_HISTORY = [
    (re.compile(GIT + r"push\b[^\n|;&]*(?:--force\b|--force-with-lease\b|\s-f\b|\s\+\S)", re.I),
     "git push --force (geçmişi yeniden yazmak, K-54)"),
    (re.compile(GIT + r"reset\b[^\n|;&]*--hard\b", re.I), "git reset --hard"),
    (re.compile(GIT + r"rebase\b", re.I), "git rebase (geçmişi yeniden yazmak, K-54)"),
    (re.compile(GIT + r"filter-(?:branch|repo)\b", re.I), "git filter-branch/filter-repo"),
]
LIVE_WRITE = [
    re.compile(r">>?\s*[\"']?" + LIVE, re.I),
    re.compile(r"\b(?:Set-Content|Add-Content|Out-File|New-Item|Move-Item|Remove-Item|Rename-Item|Clear-Content)\b"
               r"[^|;\n]*" + LIVE, re.I),
    re.compile(r"(?:^|[;&|]\s*)(?:rm|mv|del|touch|tee)\b[^|;\n]*" + LIVE, re.I),
]


# Bulgu 7 (DERS_DEFTERI 19.11): çalışma klasörü canlıyken göreli yola yazma (yönlendirme ya da yazan komut).
CD_LIVE = re.compile(r"(?:^|[;&|(\n])\s*(?:cd|chdir|Set-Location|sl|Push-Location|pushd)\s+(?:-(?:Literal)?Path\s+)?"
                     r"[\"']?" + LIVE, re.I)
WRITE_CMDS = {"set-content", "add-content", "out-file", "new-item", "ni", "clear-content", "rename-item",
              "move-item", "remove-item", "copy-item", "tee-object", "tee", "touch", "rm", "mv", "del", "cp", "sc", "ac"}
SAFE_TARGET = re.compile(r"^(?:\$null|/dev/null|nul|&\d?)$", re.I)
# Mutlak ya da değişkenli yol ($env:TEMP, $HOME, ~, %TEMP%): göreli sayılmaz; canlı mutlak yol LIVE_WRITE'ta yakalanır.
ABS_PATH = re.compile(r"^(?:[a-z]:[\\/]|\\\\|/|\$|~|%)", re.I)
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?")


def _strip_bodies(cmd: str) -> str:
    """Heredoc ve PowerShell here-string gövdelerini çıkar (gövdedeki '>' yazma değildir)."""
    cmd = re.sub(r"@'.*?\n'@", "@''@", cmd, flags=re.S)
    cmd = re.sub(r'@".*?\n"@', '@""@', cmd, flags=re.S)
    out, lines, i = [], cmd.split("\n"), 0
    while i < len(lines):
        out.append(lines[i])
        m = HEREDOC.search(lines[i])
        i += 1
        if m:
            while i < len(lines) and lines[i].strip() != m.group(1):
                i += 1
            i += 1
    return "\n".join(out)


def _segments(cmd: str) -> list[list[tuple[str, bool]]]:
    """Komutu tırnak dışındaki ; | & ve satır sonlarından böl. Her parça (sözcük, tırnaklı mı) listesidir;
    tırnak dışındaki '>' ayrı bir sözcük olur, '>&' biçimi ('2>&1') '&' sözcüğü olarak kalır."""
    segs, words, cur, quote, quoted = [], [], "", None, False
    for ch in cmd:
        if quote:
            if ch == quote:
                quote = None
            else:
                cur += ch
            continue
        if ch in "\"'":
            quote, quoted = ch, True
            continue
        if ch in ";|&\n>" or ch.isspace():
            if cur or quoted:
                words.append((cur, quoted))
            cur, quoted = "", False
            if ch == ">":
                words.append((">", False))
            elif ch == "&" and words and words[-1] == (">", False):
                words.append(("&", False))
            elif ch in ";|&\n":
                if words:
                    segs.append(words)
                words = []
            continue
        cur += ch
    if cur or quoted:
        words.append((cur, quoted))
    if words:
        segs.append(words)
    return segs


def _relative_write(cmd: str) -> bool:
    for seg in _segments(_strip_bodies(cmd)):
        for i, (w, q) in enumerate(seg):
            if w != ">" or q or (i + 1 < len(seg) and seg[i + 1] == (">", False)):
                continue
            if i + 1 >= len(seg):
                continue
            target = seg[i + 1][0]
            if SAFE_TARGET.match(target) or ABS_PATH.match(target):
                continue
            return True
        words = [w for w, _ in seg if w != ">"]
        if words and words[0].lower() in WRITE_CMDS:
            args = [w for w, q in seg[1:] if w != ">" and (q or not w.startswith("-"))]
            if not any(ABS_PATH.match(a) for a in args):
                return True
    return False


def norm(path: str) -> str:
    p = path.replace("/", "\\").lower()
    if p.startswith("\\c\\"):
        p = "c:\\" + p[3:]
    return p


def decide(event: dict) -> str | None:
    tool = event.get("tool_name", "")
    data = event.get("tool_input") or {}
    if tool in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
        path = norm(str(data.get("file_path") or data.get("notebook_path") or ""))
        if path.startswith("c:\\projeler\\quantbist-yeni\\") or path == "c:\\projeler\\quantbist-yeni":
            return ("Canlı kurulum klasörüne elle yazılmaz (CLAUDE.md, K-54). Değişikliği "
                    "C:\\Projeler\\QuantBIST-araclar\\ altındaki bir worktree'de dalda yap; canlıya surum-kapisi götürür.")
    if tool in ("Bash", "PowerShell"):
        cmd = str(data.get("command") or "")
        for rx, label in GIT_HISTORY:
            if rx.search(cmd):
                return f"Engellendi: {label}. Geçmiş yeniden yazılmaz; geri almak için git revert kullan."
        for rx in LIVE_WRITE:
            if rx.search(cmd):
                return ("Engellendi: komut canlı kurulum klasörüne yazıyor (CLAUDE.md, K-54). "
                        "Worktree'de çalış; canlıya surum-kapisi götürür.")
        cwd = norm(str(event.get("cwd") or ""))
        live_cwd = cwd.rstrip("\\") == "c:\\projeler\\quantbist-yeni" or cwd.startswith("c:\\projeler\\quantbist-yeni\\")
        if (live_cwd or CD_LIVE.search(cmd)) and _relative_write(cmd):
            return ("Engellendi: çalışma klasörü canlı kurulum; komut göreli yola yazıyor (CLAUDE.md, K-54, "
                    "DERS_DEFTERI bulgu 7). Mutlak yol ver ya da worktree'de çalış.")
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
        reason = decide(event)
    except Exception:  # noqa: BLE001 - hook asla oturumu kilitlemesin
        return 0
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))  # ASCII kaçışlı: Windows kod sayfası bozmasın
    return 0


if __name__ == "__main__":
    sys.exit(main())
