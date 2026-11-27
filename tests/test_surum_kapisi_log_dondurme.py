"""Draft lesson line (27.11.2026): after log rotation the gate must still see the bot's start line.

quantbist.log rotated on 27.11 04:50; the "Telegram bot started" line of 22.11 moved to quantbist.log.1.
The gate read only quantbist.log, so row 2 said the healthy live bot never started and the gate stayed
closed until a restart (and a restart normally needs an install). Row 5 counts installs from the same lines.
"""

import importlib.util
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("surum_kapisi", ROOT / "scripts" / "surum_kapisi.py")
kapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kapi)


def _start(day: str, version: str) -> str:
    return f"{day} 14:45:28,878 | INFO | bot.application | QuantBIST v{version} Telegram bot started (chat_id=1)."


def _write(log_dir: Path, name: str, *lines: str) -> None:
    (log_dir / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_start_line_in_rotated_log_keeps_live_healthy(tmp_path):
    _write(tmp_path, "quantbist.log.1", _start("2026-11-22", "0.99.165"))
    _write(tmp_path, "quantbist.log", "2026-11-27 07:10:00,000 | INFO | x | tick")
    first = datetime(2026, 11, 27, 7, 0, tzinfo=timezone(timedelta(hours=3)))
    beats = [first + timedelta(minutes=5 * i) for i in range(3)]

    ok, detail = kapi.live_health(kapi.read_bot_log(tmp_path), beats, "0.99.165")

    assert ok, detail


def test_rotated_files_are_read_oldest_first(tmp_path):
    _write(tmp_path, "quantbist.log.10", "a")
    _write(tmp_path, "quantbist.log.2", "b")
    _write(tmp_path, "quantbist.log.1", "c")
    _write(tmp_path, "quantbist.log", "d")

    assert kapi.read_bot_log(tmp_path) == ["a", "b", "c", "d"]


def test_install_before_rotation_is_still_counted(tmp_path):
    _write(tmp_path, "quantbist.log.1", _start("2026-11-26", "0.99.165"), _start("2026-11-27", "0.99.166"))
    _write(tmp_path, "quantbist.log", "2026-11-27 07:10:00,000 | INFO | x | tick")

    assert kapi.installs_on(kapi.read_bot_log(tmp_path), date(2026, 11, 27)) == ["0.99.166"]
