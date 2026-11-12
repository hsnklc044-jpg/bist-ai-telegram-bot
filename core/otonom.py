"""
QuantBIST
The autonomous development's stop switch and its 21:00 summary (the user's 10.11.2026 instruction).

- /otonom_dur writes data/otonom_dur.flag. While a stop flag exists, the autonomous runs (skills `siradaki-is`,
  `surum-kapisi`) merge, install and delete nothing; they only report. The bot itself keeps running.
- /otonom_devam removes the user's flag and the automatic brake's flag (<tools>/cikti/otonom_dur.flag); only
  the user lifts a brake.
- summary_text(): the daily 21:00 message: installs today (from the bot's own start lines), what the autonomous
  run recorded (<tools>/cikti/otonom_gunluk.json: package branches, CI links, rollbacks, maturity, next job),
  the 7 SLOs, whether every local branch equals its GitHub copy and how old the newest copy of the files
  outside the repository is (L, 11.11.2026); on Saturdays the full SLO table. Information only, never a question.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from pathlib import Path

from core.config.paths import DATA_DIR, LOG_DIR

STOP_FILE = DATA_DIR / "otonom_dur.flag"
TOOLS_DIR = Path(os.environ.get("QUANTBIST_TOOLS_DIR", r"C:\Projeler\QuantBIST-araclar"))
WEEKLY_DIR = LOG_DIR / "haftalik_slo"  # K-17 correction (12.11.2026): the Saturday table also goes to a file


def brake_file() -> Path:
    return TOOLS_DIR / "cikti" / "otonom_dur.flag"


def day_file() -> Path:
    return TOOLS_DIR / "cikti" / "otonom_gunluk.json"


def stopped() -> list[Path]:
    return [p for p in (STOP_FILE, brake_file()) if p.exists()]


def stop(now: datetime, path: Path | None = None) -> str:
    path = Path(path or STOP_FILE)
    if path.exists():
        return f"⏸ Otonom geliştirme zaten durdurulmuş ({path.read_text(encoding='utf-8').strip()}). Açmak için /otonom_devam."
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{now:%d.%m.%Y %H:%M} kullanıcı /otonom_dur\n", encoding="utf-8")
    return ("⏸ Otonom geliştirme durduruldu: birleştirme, canlı kurulum ve silme yapılmaz; yalnız rapor üretilir. "
            "Bot ve günlük rapor normal çalışır. Açmak için /otonom_devam.")


def resume(paths: list[Path] | None = None) -> str:
    found = [p for p in (paths or [STOP_FILE, brake_file()]) if Path(p).exists()]
    if not found:
        return "Otonom geliştirme zaten açık; durdurma bayrağı yok."
    notes = []
    for p in found:
        notes.append(Path(p).read_text(encoding="utf-8", errors="replace").strip()[:200])
        Path(p).unlink()
    return "▶️ Otonom geliştirme yeniden açık. Kaldırılan bayrak: " + " · ".join(n or "boş" for n in notes)


def installs_today(log_lines: list[str], day: date) -> list[tuple[str, str]]:
    """(version, HH:MM) for every version change of the bot on `day`."""

    found, previous = [], None
    for line in log_lines:
        m = re.search(r"QuantBIST v([\d.]+) Telegram bot started", line)
        if not m:
            continue
        if line[:10] == day.isoformat() and previous is not None and m.group(1) != previous:
            found.append((m.group(1), line[11:16]))
        previous = m.group(1)
    return found


def changelog_title(version: str, changelog: str) -> str:
    m = re.search(rf"^## v{re.escape(version)} – [^(\n]*\(([^)\n]+)\)", changelog, re.M)
    return m.group(1) if m else "CHANGELOG'da başlık yok"


def summary_text(now: datetime, log_lines: list[str], changelog: str, slo_results, record: dict | None,
                 checks: list[str] | None = None) -> str:
    record = record or {}
    lines = [f"🤖 Otonom günlük özet ({now:%d.%m.%Y}) — yalnız bilgi"]
    flags = stopped()
    if flags:
        lines.append("⏸ Durdurma bayrağı açık: birleştirme ve kurulum yok (" + ", ".join(p.name for p in flags) + ")")
    installed = installs_today(log_lines, now.date())
    if installed:
        lines.append("Bugün kurulanlar:")
        ci = record.get("ci", {})
        branches = record.get("branches", {})
        for version, at in installed:
            extra = ""
            if branches.get(version):
                extra += f" · dallar: {', '.join(branches[version])}"
            if ci.get(version):
                extra += f" · CI: {ci[version]}"
            lines.append(f"• v{version} ({at}): {changelog_title(version, changelog)}{extra}")
    else:
        lines.append("Bugün kurulum yok.")
    lines.append(f"Geri dönüş: {record.get('rollbacks', 0)}")
    lines.append("SLO: " + " · ".join(f"{r.state} {r.name}" for r in slo_results))
    if record.get("maturity"):
        lines.append("Olgunluk: " + " · ".join(f"{k} %{v}" for k, v in record["maturity"].items()))
    lines += checks or []
    lines.append(f"Yarın sıradaki iş: {record.get('next') or 'kayıt yok'}")
    if now.weekday() == 5:
        from core.reports import slo

        lines.append("")
        lines.append("Haftalık SLO tablosu:")
        lines += slo.lines(slo_results)
    return "\n".join(lines)


def branches_line(repo: Path | None = None, run=None) -> str:
    """L madde 3: every local branch against its GitHub copy as last seen (refs/remotes/origin).
    Read only; never contacts GitHub."""

    import subprocess

    repo = Path(repo or Path(__file__).resolve().parents[1])
    run = run or (lambda args, **k: subprocess.run(args, cwd=repo, capture_output=True, text=True, encoding="utf-8",
                                                     errors="replace", timeout=30))

    def sha(ref: str) -> str | None:
        out = run(["git", "rev-parse", "-q", "--verify", ref])
        return out.stdout.strip() or None if out.returncode == 0 else None

    def contains(a: str, b: str) -> bool:
        return run(["git", "merge-base", "--is-ancestor", a, b]).returncode == 0

    try:
        names = [n for n in run(["git", "for-each-ref", "refs/heads", "--format=%(refname:short)"]).stdout.split()]
        problems = []
        for name in names:
            local, remote = sha(f"refs/heads/{name}"), sha(f"refs/remotes/origin/{name}")
            if remote is None:
                problems.append(f"{name} (GitHub'da yok)")
            elif local != remote:
                if contains(local, remote):
                    problems.append(f"{name} (GitHub ileride)")
                elif contains(remote, local):
                    problems.append(f"{name} (gönderilmemiş commit)")
                else:
                    problems.append(f"{name} (ayrışmış)")
    except Exception as exc:  # noqa: BLE001 - the summary must still go out
        return f"⚠️ Dallar: kontrol edilemedi ({type(exc).__name__})"
    if not problems:
        return f"✅ Dallar: {len(names)} yerel dal GitHub'daki kopyasıyla aynı"
    return f"⚠️ Dallar: {len(names)} dalın {len(problems)}'ü farklı: " + ", ".join(problems)


OUTSIDE_PATTERN = "quantbist_depo_disi_*.zip"
OUTSIDE_MAX_DAYS = 7


def outside_copy_line(folder: Path | None, now: datetime) -> str:
    """L madde 3: the newest copy of the files outside the repository in the backup folder."""

    try:
        if folder is None:
            from core.backup import backup_dir

            folder = backup_dir()
        copies = sorted(Path(folder).glob(OUTSIDE_PATTERN), key=lambda p: p.stat().st_mtime)
    except OSError:
        copies = []
    if not copies:
        return "⚠️ Depo dışı dosyalar: yedekte kopyası yok"
    at = datetime.fromtimestamp(copies[-1].stat().st_mtime, tz=now.tzinfo)
    days = (now - at).days
    mark = "✅" if days <= OUTSIDE_MAX_DAYS else "⚠️"
    return f"{mark} Depo dışı dosyalar: son kopya {at:%d.%m} ({days} gün önce)"


def build_summary(now: datetime) -> str:
    from core.reports import slo

    log_path = LOG_DIR / "quantbist.log"
    log = log_path.read_text(encoding="utf-8", errors="replace").splitlines() if log_path.exists() else []
    root = Path(__file__).resolve().parents[1]
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8") if (root / "CHANGELOG.md").exists() else ""
    try:
        record = json.loads(day_file().read_text(encoding="utf-8"))
        if record.get("day") != now.date().isoformat():
            record = {"next": record.get("next")}
    except (OSError, ValueError):
        record = None
    checks = [branches_line(), outside_copy_line(None, now)]
    return summary_text(now, log, changelog, slo.measure(now), record, checks=checks)


def save_weekly(now: datetime, text: str) -> Path | None:
    """Saturday: the summary with the weekly SLO table, also as logs/haftalik_slo/YYYY-MM-DD.txt (K-17).

    Other days write nothing. The folder is in logs/ (not tracked by git); the bot never writes into docs/."""

    if now.weekday() != 5:
        return None
    path = WEEKLY_DIR / f"{now:%Y-%m-%d}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")
    return path


__all__ = ["STOP_FILE", "brake_file", "branches_line", "build_summary", "changelog_title", "installs_today", "resume", "save_weekly", "stop",
           "stopped", "summary_text"]
