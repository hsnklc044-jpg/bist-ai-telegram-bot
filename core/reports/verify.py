"""
QuantBIST
One text that proves an installation works, ready to paste into the chat.

    python -m core.reports.verify            # scripts\\verify.ps1 runs this after setup.ps1 -CheckOnly

Sections: version, /durum checks, a fresh price store backup and the
restore test (in a temporary folder; live files are not touched), the
last report runs and the end of the newest daily log. The bot token and
the chat id are replaced before anything is printed or written, so the
text can be shared.
"""

from __future__ import annotations

import argparse
import os
import re
from collections.abc import Callable
from pathlib import Path

from core import __version__
from core.config.paths import LOG_DIR

REPORT_FILE = LOG_DIR / "verify_report.txt"
RUN_ROWS = 7
LOG_LINES = 30
TOKEN_PATTERN = re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b")


def redact(text: str, secrets: dict[str, str] | None = None) -> str:
    """Replace the bot token, the chat id and anything shaped like a Telegram token."""

    if secrets is None:
        import core.infrastructure.settings  # noqa: F401 - loads .env into the environment

        secrets = {name: os.getenv(name, "").strip()
                   for name in ("BOT_TOKEN", "CHAT_ID", "HC_REPORT_URL", "HC_BOT_URL")}
    for name, value in secrets.items():
        if value and len(value) >= 4:
            text = text.replace(value, f"[{name}]")
    return TOKEN_PATTERN.sub("[BOT_TOKEN]", text)


def _section(title: str, build: Callable[[], str]) -> list[str]:
    try:
        body = build()
    except Exception as exc:  # noqa: BLE001 - a failed section is reported, the others still run
        body = f"HATA: {type(exc).__name__}: {exc}"
    return [f"== {title} ==", body.rstrip(), ""]


def _backup() -> str:
    from core.backup import backup_market_db, test_restore

    snapshot = backup_market_db()
    lines = [snapshot.line() if snapshot else "Fiyat veritabanı yok, anlık yedek alınmadı."]
    lines += test_restore()
    lines.append("Geri yükleme testi başarılı (canlı dosyalara dokunulmadı).")
    return "\n".join(lines)


def _runs(path: Path | None = None) -> str:
    from core.reports import runs

    path = Path(path or runs.RUNS_FILE)
    if not path.exists():
        return f"{path.name} yok"
    rows = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(rows[:1] + rows[1:][-RUN_ROWS:])


def _daily_log(folder: Path | None = None) -> str:
    folder = Path(folder or LOG_DIR)
    logs = sorted(folder.glob("daily_*.log"))
    if not logs:
        return "günlük rapor logu yok"
    lines = logs[-1].read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join([logs[-1].name, *lines[-LOG_LINES:]])


def _health() -> str:
    from core.reports.health import health_report

    return health_report()


def verify_report(backup: bool = True, secrets: dict[str, str] | None = None,
                  runs_file: Path | None = None, log_dir: Path | None = None) -> str:
    lines = [f"QuantBIST v{__version__} doğrulama raporu", ""]
    lines += _section("Sağlık (/durum ile aynı kontroller)", _health)
    if backup:
        lines += _section("Yedek ve geri yükleme testi", _backup)
    lines += _section(f"Son rapor çalıştırmaları (logs/runs.csv, son {RUN_ROWS})", lambda: _runs(runs_file))
    lines += _section(f"Son günlük rapor logu (son {LOG_LINES} satır)", lambda: _daily_log(log_dir))
    return redact("\n".join(lines), secrets)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Installation proof, safe to share.")
    parser.add_argument("--no-backup", action="store_true", help="skip the backup and the restore test")
    parser.add_argument("--out", type=Path, default=REPORT_FILE)
    args = parser.parse_args(argv)

    text = verify_report(backup=not args.no_backup)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(text)
    print(f"Yazıldı: {args.out}")
    return 1 if "HATA:" in text else 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["redact", "verify_report"]
