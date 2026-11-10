"""
QuantBIST
Release gate (10.11.2026, the user's delegation; docs/OPERATIONS.md §5a, skill `surum-kapisi`).

    python scripts/surum_kapisi.py SHA [--testler-gecti] [--birlestir] [--slo-kaydet]

Checks every condition and prints ✅/❌ per line. With --birlestir and every condition passed, the bot branch
is fast-forwarded to SHA (never a force push). Nothing is ever written into the live folder: the live folder
is only read (git, logs). Run from a worktree, never from the live folder.

Conditions (all required):
1. tests and ruff passed locally on SHA (declared with --testler-gecti) and the CI run of SHA is green;
2. the live version is healthy: its SHA and version, a "Telegram bot started" line and >= 3 heartbeats without
   an ERROR since that start;
3. no SLO is worse than at the previous install (cikti/slo_son.json);
4. the install (the updater's next :40 run after CI) is outside 09:40-18:15 and 18:00-20:00 on a session day
   (weekends and holidays are open all day; the updater runs 07:40-23:40);
5. one package at a time (the bot branch equals the live SHA) and at most 4 installs a day.
Also: no stop flag, no local change in the live folder, the chain is a fast-forward, and a change to the
updater, backup, restore or personal record format never goes in a package (asked, installed alone).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

LIVE = Path(r"C:\Projeler\QuantBIST-yeni")
TOOLS = Path(r"C:\Projeler\QuantBIST-araclar")
OUT = TOOLS / "cikti"
BRANCH = "claude/borsa-bot-creation-n7nmc9"
REPO = "hsnklc044-jpg/bist-ai-telegram-bot"
STOP_FLAGS = (LIVE / "data" / "otonom_dur.flag", OUT / "otonom_dur.flag")
LOCK = OUT / "birlestirme.lock"
MAX_INSTALLS = 4
CI_MINUTES = 25
UPDATER_FIRST, UPDATER_LAST = 7, 23  # "QuantBIST Guncelle": 07:40 then hourly for 16 hours
ALONE = ("scripts/guncelle.py", "scripts/register_update_task.ps1", "core/backup.py", "core/infrastructure/csvfiles.py",
         "core/signals/store.py", "setup.ps1", "requirements.lock")
RANK = {"✅": 0, "❔": 1, "⚠️": 2, "🛑": 3}


# --- pure rules (tested) --------------------------------------------------------------------------

def next_install(merged: datetime, ci_minutes: int = CI_MINUTES) -> datetime:
    """The updater's first run after CI is green: hourly at :40 from 07:40 to 23:40; 18:00-20:00 it waits for
    the daily report, so a run in that window installs nothing."""

    t = (merged + timedelta(minutes=ci_minutes)).replace(second=0, microsecond=0)
    t = t.replace(minute=40) if t.minute <= 40 else (t + timedelta(hours=1)).replace(minute=40)
    while True:
        if t.hour < UPDATER_FIRST:
            t = t.replace(hour=UPDATER_FIRST, minute=40)
        elif t.hour > UPDATER_LAST:
            t = (t + timedelta(days=1)).replace(hour=UPDATER_FIRST, minute=40)
        elif 18 <= t.hour < 20:
            t = t.replace(hour=20, minute=40)
        else:
            return t


def window_ok(at: datetime, session_day: bool) -> tuple[bool, str]:
    if not session_day:
        return True, f"{at:%a %d.%m %H:%M} seans günü değil, pencere açık"
    m = at.hour * 60 + at.minute
    if 9 * 60 + 40 <= m <= 18 * 60 + 15:
        return False, f"{at:%a %d.%m %H:%M} seans saatinde (09:40–18:15)"
    if 18 * 60 <= m <= 20 * 60:
        return False, f"{at:%a %d.%m %H:%M} rapor penceresinde (18:00–20:00)"
    return True, f"{at:%a %d.%m %H:%M} seans ve rapor penceresi dışında"


def installs_on(log_lines: list[str], day: date) -> list[str]:
    """Versions installed on `day`: a "Telegram bot started" line whose version differs from the one before."""

    found, previous = [], None
    for line in log_lines:
        m = re.search(r"QuantBIST v([\d.]+) Telegram bot started", line)
        if not m:
            continue
        if line[:10] == day.isoformat() and previous is not None and m.group(1) != previous:
            found.append(m.group(1))
        previous = m.group(1)
    return found


def slo_worse(previous: dict, current: dict, tolerance: float = 0.005) -> list[str]:
    """SLOs whose state is worse, or whose value fell by more than `tolerance`, than at the previous install."""

    worse = []
    for name, (state, value) in current.items():
        if name not in previous:
            continue
        p_state, p_value = previous[name]
        if RANK.get(state, 9) > RANK.get(p_state, 9):
            worse.append(f"{name}: {p_state} → {state}")
        elif value is not None and p_value is not None and value < p_value - tolerance:
            worse.append(f"{name}: {p_value:.3f} → {value:.3f}")
    return worse


def live_health(log_lines: list[str], beats: list[datetime], version: str) -> tuple[bool, str]:
    starts = [ln for ln in log_lines if f"QuantBIST v{version} Telegram bot started" in ln]
    if not starts:
        return False, f"v{version} için 'Telegram bot started' satırı yok"
    started = datetime.fromisoformat(starts[-1][:19])
    errors = [ln for ln in log_lines if ln[:19] >= started.isoformat(sep=" ") and "| ERROR |" in ln]
    after = [b for b in beats if b.replace(tzinfo=None) >= started]
    ok = len(after) >= 3 and not errors
    return ok, (f"v{version} başlangıç {started:%d.%m %H:%M}; sonrasında {len(after)} yaşam sinyali, {len(errors)} ERROR"
                + (f" (ilk: {errors[0][:100]})" if errors else ""))


def alone_files(changed: list[str]) -> list[str]:
    return [f for f in changed if f in ALONE]


# --- the live facts (read only) -------------------------------------------------------------------

def _git(*args, cwd=LIVE) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def _ci(sha: str) -> tuple[bool, str]:
    try:
        url = f"https://api.github.com/repos/{REPO}/actions/runs?head_sha={sha}"
        runs = [r for r in json.load(urllib.request.urlopen(url, timeout=15)).get("workflow_runs", [])
                if r.get("name") == "CI"]
    except Exception as exc:  # noqa: BLE001
        return False, f"CI sorgulanamadı ({type(exc).__name__})"
    if not runs:
        return False, "CI çalışması yok"
    ok = all(r["status"] == "completed" and r["conclusion"] == "success" for r in runs)
    return ok, ", ".join(f"{r['status']}/{r['conclusion']} {r['html_url']}" for r in runs)


def _slo_now() -> dict:
    sys.path.insert(0, str(LIVE))
    import logging

    logging.disable(logging.CRITICAL)
    from core.market.calendar import now_istanbul
    from core.reports import slo

    return {r.name: (r.state, r.value) for r in slo.measure(now_istanbul())}


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sha = argv[0]
    tests_ok, merge, save = "--testler-gecti" in argv, "--birlestir" in argv, "--slo-kaydet" in argv
    here = Path.cwd().resolve()
    if here == LIVE.resolve() or LIVE.resolve() in here.parents:
        print("❌ canlı klasörden çalıştırılamaz; bir worktree'den çalıştır")
        return 2
    results = []

    def check(name, ok, detail):
        results.append(ok)
        print(f"{'✅' if ok else '❌'} {name}: {detail}")

    flags = [str(f) for f in STOP_FLAGS if f.exists()]
    check("0 durdurma bayrağı yok", not flags, flags or "yok")
    dirty = _git("status", "--porcelain", "--untracked-files=no")
    check("0 canlı klasörde yerel değişiklik yok", not dirty, dirty[:200] or "temiz")

    ci_ok, ci_text = _ci(sha)
    check("1 tam test + ruff yerelde, CI yeşil", tests_ok and ci_ok,
          f"yerel {'geçti (beyan)' if tests_ok else 'BEYAN YOK'}; CI {ci_text}")

    subprocess.run(["git", "fetch", "-q", "origin", BRANCH], cwd=here)
    head = _git("rev-parse", "HEAD")
    version = re.search(r'^version = "([^"]+)"', _git("show", "HEAD:pyproject.toml"), re.M).group(1)
    log = (LIVE / "logs" / "quantbist.log").read_text(encoding="utf-8", errors="replace").splitlines()
    beats = [datetime.fromisoformat(r.split(",")[0])
             for r in (LIVE / "logs" / "heartbeats.csv").read_text(encoding="utf-8").splitlines()[1:] if r]
    ok, detail = live_health(log, beats, version)
    check("2 canlı sürüm sağlıklı", ok, f"canlı {head[:7]} {detail}")

    current = _slo_now()
    prev_file = OUT / "slo_son.json"
    previous = json.loads(prev_file.read_text(encoding="utf-8")) if prev_file.exists() else {}
    worse = slo_worse(previous, current)
    check("3 hiçbir SLO kötüleşmedi", bool(previous) and not worse,
          "önceki kayıt yok" if not previous else (worse or "aynı ya da daha iyi"))
    critical = [n for n, (s, _) in current.items() if s == "🛑"]
    if critical:
        print(f"🛑 FREN: KRİTİK SLO {critical}")

    sys.path.insert(0, str(LIVE))
    from core.market.calendar import is_session_day

    at = next_install(datetime.now())
    ok, detail = window_ok(at, is_session_day(at.date()))
    check("4 kurulum zamanı", ok, detail)

    tip = _git("rev-parse", f"origin/{BRANCH}", cwd=here)
    today = installs_on(log, at.date())
    check("5 tek paket, günde ≤4 kurulum", tip == head and len(today) < MAX_INSTALLS,
          f"bot dalı {tip[:7]} / canlı {head[:7]}; {at:%d.%m} günü kurulan {len(today)} {today}")

    ff = subprocess.run(["git", "merge-base", "--is-ancestor", tip, sha], cwd=here).returncode == 0
    check("6 zincir ileri sarılabilir", ff, f"{tip[:7]} → {sha[:7]}")
    changed = _git("diff", "--name-only", tip, sha, cwd=here).splitlines()
    alone = alone_files(changed)
    check("7 paket istisnası yok (güncelleyici/yedek/geri yükleme/kayıt biçimi)", not alone, alone or "yok")

    if save:
        prev_file.write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
        print(f"SLO kaydı: {prev_file}")
    passed = all(results)
    print("KAPI:", "AÇIK" if passed else "KAPALI")
    if not (passed and merge):
        return 0 if passed else 1
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print(f"❌ başka bir oturum birleştiriyor: {LOCK}")
        return 1
    try:
        os.write(fd, f"{datetime.now():%Y-%m-%d %H:%M} {sha}\n".encode())
        push = subprocess.run(["git", "push", "origin", f"{sha}:refs/heads/{BRANCH}"], cwd=here,
                              capture_output=True, text=True)
        print(push.stdout + push.stderr)
        if push.returncode == 0:
            prev_file.write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
            print(f"BİRLEŞTİ {sha[:7]}; beklenen kurulum {at:%d.%m %H:%M}")
        return push.returncode
    finally:
        os.close(fd)
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
