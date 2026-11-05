"""
QuantBIST
Road plan part 4 (operations quality; 05.11.2026): the weekly summary the bot sends by itself every
Sunday, so a slow failure (reports missed, backups not tested, CI red, a stale drill) is seen even
when nobody asks /durum:

- the installed version;
- the service objectives of the last 7 days (core.reports.slo: report delivery, bot uptime,
  data freshness, accuracy, backup and restore test, record integrity, CI);
- the monthly disaster recovery drill (dr-drill.yml): its latest result, read from
  research-results/drills/latest.txt; older than DRILL_MAX_AGE days is a warning.
What cannot be read is "bilinmiyor", never "ok".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from core.config.paths import LOG_DIR

DRILL_URL = ("https://raw.githubusercontent.com/hsnklc044-jpg/bist-ai-telegram-bot/"
             "research-results/drills/latest.txt")
DRILL_MAX_AGE = 35  # days; the drill runs on the 3rd of each month
SENT_FILE = LOG_DIR / "weekly_summary_sent.txt"  # one line per Sunday summary sent (05.11.2026)
DUE_HOUR = 18
_DRILL = re.compile(r"DR drill (\d{4})-(\d{2})-(\d{2})_\S* \([^)]*\): (\w+)")


@dataclass(frozen=True)
class Drill:
    day: date
    passed: bool


def parse_drill(text: str) -> Drill | None:
    m = _DRILL.search(text or "")
    if not m:
        return None
    return Drill(date(int(m[1]), int(m[2]), int(m[3])), m[4].lower() == "success")


def drill_line(now: datetime, get=None) -> str:
    try:
        if get is None:
            from core.reports import health

            get = health._http_get or __import__("httpx").get
        answer = get(DRILL_URL, timeout=10)
        drill = parse_drill(answer.text) if getattr(answer, "status_code", 200) < 400 else None
    except Exception:  # noqa: BLE001 - offline: unknown, never "ok"
        drill = None
    if drill is None:
        return "❔ Felaket kurtarma tatbikatı: son sonuç okunamadı (GitHub'a ulaşılamadı ya da henüz kayıt yok)"
    age = (now.date() - drill.day).days
    if not drill.passed:
        return (f"❌ Felaket kurtarma tatbikatı: {drill.day:%d.%m.%Y} BAŞARISIZ – GitHub Actions > "
                "Disaster recovery drill çalışmasına bakın")
    if age > DRILL_MAX_AGE:
        return f"⚠️ Felaket kurtarma tatbikatı: son başarılı {drill.day:%d.%m.%Y}, {age} gün eski (her ayın 3'ünde çalışmalı)"
    return f"✅ Felaket kurtarma tatbikatı: {drill.day:%d.%m.%Y} başarılı (temiz Windows'a yedekten kurulum)"


def summary(now: datetime | None = None) -> str:
    import core
    from core.market.calendar import now_istanbul
    from core.reports import slo

    now = now or now_istanbul()
    lines = [f"🗒 Haftalık işletme özeti ({now:%d.%m.%Y}) – kurulu sürüm v{core.__version__}"]
    try:
        lines += slo.lines(slo.measure(now))
    except Exception as exc:  # noqa: BLE001 - the summary still goes out
        lines.append(f"📐 SLO ölçülemedi: {type(exc).__name__}: {str(exc)[:150]}")
    lines.append(drill_line(now))
    lines.append("Ayrıntı: /durum tum. Bir hedef tutmuyorsa önce o düzeltilir (CHARTER §4).")
    return "\n".join(lines)


# --- the summary's own watch (05.11.2026: it watches everything but itself) ---------------------


def _local(moment: datetime) -> datetime:
    from core.market.calendar import ISTANBUL

    return moment.astimezone(ISTANBUL).replace(tzinfo=None) if moment.tzinfo else moment


def record_sent(now: datetime, path: Path | None = None) -> None:
    path = Path(path or SENT_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(_local(now).isoformat(timespec="seconds") + "\n")


def last_sent(path: Path | None = None) -> datetime | None:
    try:
        lines = Path(path or SENT_FILE).read_text(encoding="utf-8").split()
    except OSError:
        return None
    stamps = []
    for line in lines:
        try:
            stamps.append(datetime.fromisoformat(line))
        except ValueError:
            continue
    return max(stamps, default=None)


def missing_warning(now: datetime, path: Path | None = None) -> str | None:
    """A warning when the last Sunday's summary (due 18:00) was not sent; None when it was."""

    now = _local(now)
    sunday = now.date() - timedelta(days=(now.weekday() + 1) % 7)
    due = datetime(sunday.year, sunday.month, sunday.day, DUE_HOUR)
    if due > now:
        due -= timedelta(days=7)
    last = last_sent(path)
    if last is not None and last >= due:
        return None
    before = f"son gönderim {last:%d.%m.%Y %H:%M}" if last else "hiç gönderim kaydı yok"
    return (f"⚠️ {due:%d.%m.%Y} pazar 18:00 haftalık işletme özeti gönderilmedi ({before}). Bot o saatte kapalı "
            "olabilir ya da iş hata vermiş olabilir: /durum ve logs/quantbist.log'a bakın. /ozet ile şimdi alabilirsiniz.")


__all__ = ["DRILL_MAX_AGE", "Drill", "SENT_FILE", "drill_line", "last_sent", "missing_warning", "parse_drill",
           "record_sent", "summary"]
