"""Install the newest QuantBIST release whose CI passed, safely and unattended (Windows PC).

    C:\\Projeler\\QuantBIST\\.venv\\Scripts\\python.exe C:\\Projeler\\QuantBIST\\scripts\\guncelle.py [--no-restart]

Run every morning by the "QuantBIST Guncelle" task (DECISIONS K-27, K-29). Steps, each one a
gate (a failure stops before the live folder changes):
1. The newest commit of the branch whose CI run succeeded (GitHub API); its version must be
   newer than the installed one, else nothing to do. A red or running CI is never installed.
2. Back up the personal records (core.backup).
3. Download and extract exactly that commit next to the project.
4. requirements.lock changed -> test the new packages in a throwaway venv first.
5. Staging: copy the release plus the live data (.env excluded) to a temporary folder, run
   ruff and the tests there.
6. Snapshot the live code (personal files excluded), copy the release in.
7. Restart the Telegram bot through its task and check it stays up; if it does not, put the
   snapshot back and start the old version again.
8. Every outcome except "nothing new" goes to Telegram (bildir.py).

Personal files (.env, watchlist.json, logs, backups) are never copied over.
The last line printed is a one-line summary; the full log goes to
C:\\Projeler\\QuantBIST_otomasyon\\logs\\guncelle_<time>.log.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

PROJECT = Path(r"C:\Projeler\QuantBIST")
HOME = Path(r"C:\Projeler")
AUTO = Path(r"C:\Projeler\QuantBIST_otomasyon")  # lock and logs (outside the project)
PYTHON = PROJECT / ".venv" / "Scripts" / "python.exe"
PYTHONW = PROJECT / ".venv" / "Scripts" / "pythonw.exe"
BRANCH = "claude/borsa-bot-creation-n7nmc9"
REPO = "hsnklc044-jpg/bist-ai-telegram-bot"
API = f"https://api.github.com/repos/{REPO}/actions/workflows/ci.yml/runs"

# never copied from a release into the live folder
EXCLUDE_FILES = [".env", "watchlist.json"]
EXCLUDE_DIRS = [".venv", "logs", "backups", ".git"]
# left out of the code snapshot (personal or bulky, and never overwritten anyway)
SNAPSHOT_EXCLUDE_DIRS = [".venv", "logs", "data", ".git", "__pycache__", ".pytest_cache", ".ruff_cache"]
QUIET = ("GÜNCEL", "MEŞGUL")  # outcomes that are not worth a message

ENV = {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
LOG: list[str] = []


def log(msg: str) -> None:
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    LOG.append(line)


def fetch(url: str) -> bytes:
    headers = {"User-Agent": "QuantBIST-guncelle"}
    if url.startswith(API):  # the API's media type only for the API (not the zip or raw file)
        headers["Accept"] = "application/vnd.github+json"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def version_of(text: str) -> str:
    m = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not m:
        raise RuntimeError("sürüm numarası okunamadı")
    return m.group(1)


def newer(candidate: str, installed: str) -> bool:
    return tuple(int(x) for x in candidate.split(".")) > tuple(int(x) for x in installed.split("."))


def latest_green(get=fetch) -> str | None:
    """SHA of the newest commit on BRANCH whose CI run succeeded; None if there is none."""

    query = urllib.parse.urlencode({"branch": BRANCH, "status": "success", "per_page": 1})
    runs = json.loads(get(f"{API}?{query}")).get("workflow_runs") or []
    for run_ in runs:
        if run_.get("head_branch") == BRANCH and run_.get("conclusion") == "success":
            return run_["head_sha"]
    return None


def version_url(sha: str) -> str:
    return f"https://raw.githubusercontent.com/{REPO}/{sha}/core/__init__.py"


def zip_url(sha: str) -> str:
    return f"https://github.com/{REPO}/archive/{sha}.zip"


def should_notify(summary: str) -> bool:
    return not summary.startswith(QUIET)


def notify(summary: str) -> None:
    """The result to Telegram; a failed message is logged, never fatal."""

    try:
        proc = run([str(PYTHON), str(Path(__file__).with_name("bildir.py")), summary], cwd=PROJECT, timeout=120)
        if proc.returncode != 0:
            log("Telegram'a bildirilemedi")
    except Exception as exc:  # noqa: BLE001
        log(f"Telegram'a bildirilemedi: {exc}")


def run(cmd: list, cwd: Path, timeout: int = 900) -> subprocess.CompletedProcess:
    import os

    env = {**os.environ, **ENV}
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-15:]
    log(f"$ {' '.join(str(c) for c in cmd)} -> {proc.returncode}")
    for t in tail:
        LOG.append("    " + t)
    return proc


def robocopy(src: Path, dst: Path, xf: list[str], xd: list[str]) -> None:
    proc = run(["robocopy", str(src), str(dst), "/E", "/NFL", "/NDL", "/NP", "/R:2", "/W:2",
                "/XF", *xf, "/XD", *xd], cwd=HOME)
    if proc.returncode >= 8:  # robocopy: 0-7 success, 8+ failure
        raise RuntimeError(f"robocopy {src} -> {dst} başarısız ({proc.returncode})")


def bot_processes() -> list[int]:
    """PIDs of the running bot: the venv launcher of main.py (its child, the
    base interpreter, is stopped with it by taskkill /T)."""
    ps = ("Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
          "Where-Object { $_.CommandLine -match 'QuantBIST\\\\\\.venv' -and $_.CommandLine -match 'main\\.py' } | "
          "ForEach-Object { $_.ProcessId }")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    return [int(x) for x in out.split() if x.isdigit()]


BOT_TASK = "QuantBIST Bot"  # Windows task that starts the bot at logon; when present it owns the bot


def bot_task_exists() -> bool:
    return subprocess.run(["schtasks", "/Query", "/TN", BOT_TASK], capture_output=True).returncode == 0


def stop_bot() -> None:
    if bot_task_exists():
        subprocess.run(["schtasks", "/End", "/TN", BOT_TASK], capture_output=True)
        log(f"'{BOT_TASK}' görevi durduruldu")
        time.sleep(3)
    for pid in bot_processes():  # anything the task did not own (or left behind)
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        log(f"bot durduruldu (PID {pid})")
    time.sleep(3)


def start_bot() -> bool:
    """Start the bot (through its Windows task when there is one, so only one
    bot ever runs); True when it is still running after 45 s."""
    import os

    if bot_processes():
        log("bot zaten çalışıyor; ikinci kopya başlatılmadı")
        return True
    if bot_task_exists():
        subprocess.run(["schtasks", "/Run", "/TN", BOT_TASK], capture_output=True)
        log(f"bot '{BOT_TASK}' göreviyle başlatıldı")
    else:
        subprocess.Popen([str(PYTHONW), "main.py"], cwd=PROJECT, env={**os.environ, **ENV},
                         creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(45)
    alive = bool(bot_processes())
    log("bot çalışıyor" if alive else "bot başlamadı / kapandı")
    return alive


def main(argv: list[str]) -> int:
    # one updater at a time (scheduled task and a manual run may overlap); a lock older than
    # 1 h is stale; the lock holds the owner's PID: a lock left by an interrupted run is taken over
    import os

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    AUTO.mkdir(parents=True, exist_ok=True)
    lock = AUTO / "guncelle.lock"
    if lock.exists() and time.time() - lock.stat().st_mtime < 3600:
        owner = lock.read_text(encoding="utf-8").split()[0] if lock.read_text(encoding="utf-8").strip() else ""
        alive = owner.isdigit() and subprocess.run(
            ["tasklist", "/FI", f"PID eq {owner}", "/NH"], capture_output=True, text=True, errors="replace"
        ).stdout.strip().split(" ")[0].lower().startswith("python")
        if alive:
            print("ÖZET: MEŞGUL: başka bir güncelleme sürüyor, bu çalışma atlandı.")
            return 0
        print(f"yarım kalmış kilit bulundu (sahibi {owner or 'bilinmiyor'} çalışmıyor), devralındı")
    lock.write_text(f"{os.getpid()} {datetime.now()}", encoding="utf-8")
    try:
        return _main(argv)
    finally:
        lock.unlink(missing_ok=True)


def _main(argv: list[str]) -> int:
    restart = "--no-restart" not in argv
    stamp = f"{datetime.now():%Y%m%d-%H%M}"
    (AUTO / "logs").mkdir(parents=True, exist_ok=True)
    summary = "bilinmiyor"
    code = 1
    try:
        installed = version_of((PROJECT / "core" / "__init__.py").read_text(encoding="utf-8"))
        sha = latest_green()
        if sha is None:
            summary = f"DURDU: GitHub'da CI'ı yeşil bir sürüm bulunamadı; v{installed} çalışmaya devam ediyor."
            return code
        latest = version_of(fetch(version_url(sha)).decode("utf-8"))
        log(f"kurulu {installed}, GitHub'da CI'ı yeşil son sürüm {latest} ({sha[:7]})")
        if not newer(latest, installed):
            summary = f"GÜNCEL: v{installed} kurulu, yeni sürüm yok."
            code = 0
            return code

        if run([str(PYTHON), "-m", "core.backup"], cwd=PROJECT).returncode != 0:
            summary = f"DURDU: yedek alınamadı, v{latest} kurulmadı."
            return code

        release_dir = HOME / f"QuantBIST_v{latest}"
        zip_path = HOME / f"QuantBIST_v{latest}.zip"
        if release_dir.exists():
            shutil.rmtree(release_dir)
        zip_path.write_bytes(fetch(zip_url(sha)))
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(release_dir)
        src = next(p for p in release_dir.iterdir() if p.is_dir())
        if version_of((src / "core" / "__init__.py").read_text(encoding="utf-8")) != latest:
            summary = "DURDU: indirilen zip beklenen sürüm değil; sonra tekrar denenecek."
            return code
        log(f"indirildi: {src} ({sha[:7]})")

        packages_changed = (src / "requirements.lock").read_bytes() != (PROJECT / "requirements.lock").read_bytes()

        stage = Path(tempfile.mkdtemp(prefix="quantbist_stage_"))
        try:
            # the release plus the live data only: local work folders in the project (backups\, qb\,
            # research_workspace\ ...) are not part of the release and must not decide the gate
            robocopy(src, stage, EXCLUDE_FILES, EXCLUDE_DIRS)
            robocopy(PROJECT / "data", stage / "data", [], ["backups"])
            python = PYTHON
            if packages_changed:
                # new package set: test it in a throwaway venv before touching the live one
                log("paket listesi değişmiş; geçici sanal ortam kuruluyor")
                if run(["py", "-3.11", "-m", "venv", str(stage / ".venv")], cwd=stage).returncode != 0:
                    summary = f"KURULMADI: v{latest} için geçici sanal ortam kurulamadı. v{installed} çalışmaya devam ediyor."
                    return code
                python = stage / ".venv" / "Scripts" / "python.exe"
                pip = run([str(python), "-m", "pip", "install", "-q", "-r", "requirements.lock"], cwd=stage, timeout=1800)
                if pip.returncode != 0:
                    summary = f"KURULMADI: v{latest} paketleri kurulamadı (pip {pip.returncode}). v{installed} çalışmaya devam ediyor."
                    return code
            ruff = run([str(python), "-m", "ruff", "check", "--no-cache", "."], cwd=stage)
            tests = run([str(python), "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=stage, timeout=1800)
            result = (tests.stdout.strip().splitlines() or ["?"])[-1]
            if ruff.returncode != 0 or tests.returncode != 0:
                summary = (f"KURULMADI: v{latest} deneme kopyasında başarısız (ruff {ruff.returncode}; {result}). "
                           f"v{installed} çalışmaya devam ediyor.")
                return code
            log(f"deneme kopyası: {result}")
        finally:
            shutil.rmtree(stage, ignore_errors=True)

        if packages_changed:
            pip = run([str(PYTHON), "-m", "pip", "install", "-q", "-r", str(src / "requirements.lock")], cwd=PROJECT, timeout=1800)
            if pip.returncode != 0:
                summary = f"KURULMADI: canlı ortamda paket kurulumu başarısız (pip {pip.returncode}). v{installed} çalışmaya devam ediyor."
                return code
            result += "; paketler güncellendi"

        snapshot = HOME / f"QuantBIST_onceki_v{installed}_{stamp}"
        robocopy(PROJECT, snapshot, [".env"], SNAPSHOT_EXCLUDE_DIRS)

        if restart:
            stop_bot()
        robocopy(src, PROJECT, EXCLUDE_FILES, EXCLUDE_DIRS)
        now = version_of((PROJECT / "core" / "__init__.py").read_text(encoding="utf-8"))
        if restart:
            # the bot task restarts the bot by itself, possibly mid-copy: stop it once more so
            # whatever runs from here on was started from the new files
            stop_bot()

        if restart and not start_bot():
            log("geri alınıyor")
            stop_bot()
            robocopy(snapshot, PROJECT, [], [])
            stop_bot()
            ok = start_bot()
            summary = (f"GERİ ALINDI: v{latest} kuruldu ama bot açılmadı; v{installed} geri yüklendi"
                       f"{' ve bot çalışıyor' if ok else ', BOT KAPALI — müdahale gerekiyor'}.")
            return code

        summary = f"KURULDU: v{installed} → v{now}. {result}; ruff temiz" + ("; bot yeniden başlatıldı." if restart else ".")
        code = 0
        return code
    except Exception as exc:  # noqa: BLE001 - reported, never silent
        summary = f"HATA: {type(exc).__name__}: {exc}"
        log(summary)
        return 1
    finally:
        log(summary)
        (AUTO / "logs" / f"guncelle_{stamp}.log").write_text("\n".join(LOG) + "\n", encoding="utf-8")
        print("ÖZET: " + summary)
        if should_notify(summary):
            notify(summary)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
