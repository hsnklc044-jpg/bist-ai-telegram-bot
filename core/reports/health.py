"""
QuantBIST
System health (/durum): is the daily chain actually working?

Every line is read from evidence: logs/runs.csv, the price store and its
SQLite integrity, data/signal_log.csv, data/equity_log.csv, the backup
folder, the bot's heartbeat file, free disk space, the headers of the
personal files and the last GitHub research run.

States: SAĞLIKLI, UYARI, KRİTİK, BİLİNMİYOR. A check that cannot be made
is BİLİNMİYOR, never SAĞLIKLI.

The Windows scheduled task itself is not visible from here; its work
shows up in logs/runs.csv.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from core import __version__
from core.config.paths import (
    ALERTS_LOG_FILE,
    DATA_DIR,
    EQUITY_LOG_FILE,
    FUNDAMENTALS_FILE,
    LEDGER_FILE,
    LOG_DIR,
    MARKET_DB,
    PAPER_ORDERS_FILE,
    PRICE_ALARMS_FILE,
    SCREEN_SUBSCRIPTIONS_FILE,
    SCREEN_VIRTUAL_FILE,
    SCREENS_FILE,
    SIGNAL_LOG_FILE,
)
from core.market.calendar import (
    ISTANBUL,
    SESSION_FINAL,
    covered_until,
    holidays,
    last_final_session_date,
    now_istanbul,
    sessions_between,
)
from core.infrastructure.logger import get_logger
from core.market.universe import BENCHMARK
from core.reports import runs as run_log
from core.reports.daily import adjusted_bars, tr
from core.signals_log import audit_log

logger = get_logger(__name__)

OK, WARN, CRIT, UNKNOWN = "✅", "⚠️", "🛑", "❔"
INFO = "ℹ️"  # a fact, not a problem: never changes the verdict, never alerts
LABELS = {OK: "SAĞLIKLI", WARN: "UYARI", CRIT: "KRİTİK", UNKNOWN: "BİLİNMİYOR", INFO: "BİLGİ"}
BOT_PING_STALE = timedelta(minutes=20)  # Healthchecks "QuantBIST bot": 5 min period, 20 min grace
HEARTBEAT_FILE = LOG_DIR / "heartbeat.txt"
HEARTBEAT_STALE = timedelta(minutes=20)  # the bot writes it every 5 minutes
DISK_WARN, DISK_CRIT = 1_000_000_000, 200_000_000  # free bytes
BACKUP_CRIT_AGE = timedelta(days=10)
RESEARCH_MAX_AGE = timedelta(days=8)  # weekly on Saturdays
_http_get = None  # tests replace it so that no test reaches the network
RESEARCH_API = "https://api.github.com/repos/hsnklc044-jpg/bist-ai-telegram-bot/actions/workflows/research.yml/runs"

BACKUP_MAX_AGE = timedelta(days=4)


@dataclass
class Check:
    name: str
    state: str
    text: str

    def line(self) -> str:
        return f"{self.state} {LABELS[self.state]} · {self.name}: {self.text}"


def _date(day: date) -> str:
    return day.strftime("%d.%m.%Y")


def _session_start(day: date) -> datetime:
    return datetime.combine(day, SESSION_FINAL, tzinfo=ISTANBUL)


def due_session(now: datetime) -> date:
    """The latest session whose daily report should already have gone out (core.market.calendar)."""

    from core.market.calendar import report_due_day

    return report_due_day(now)


def report_check(now: datetime, path: Path | str | None = None) -> Check:
    rows = run_log.read_runs(path)
    done = [r for r in rows if r.status in (run_log.SENT, "skipped", "holiday")]
    sent = [r for r in rows if r.status == run_log.SENT]

    if not done:
        return Check("Günlük rapor", UNKNOWN, "henüz gönderim kaydı yok (kayıt v0.22.0 ile başladı)")

    last = sent[-1] if sent else None
    text = (
        f"son gönderilen {_date(date.fromisoformat(last.data_day))} kapanışı "
        f"({datetime.fromisoformat(last.started_at):%d.%m %H:%M})"
        if last
        else "gönderilmiş rapor yok"
    )

    due = due_session(now)
    covered = any(datetime.fromisoformat(r.started_at) >= _session_start(due) for r in done)
    failed = [r for r in rows if r.status == "failed"]
    if failed and (not done or failed[-1].started_at > done[-1].started_at):
        return Check("Günlük rapor", CRIT, f"{text}; son çalıştırma hata verdi: {failed[-1].detail}")
    stale = [r for r in rows if r.status == "stale" and datetime.fromisoformat(r.started_at) >= _session_start(due)]
    if not covered and stale:
        return Check("Günlük rapor", WARN, f"{text}; {_date(due)} kapanış verisi gelmedi ({stale[-1].detail})")
    if not covered:
        return Check("Günlük rapor", CRIT, f"{text}; {_date(due)} kapanış raporu gitmedi")

    return Check("Günlük rapor", OK, text)


def price_check(now: datetime, bars=adjusted_bars) -> Check:
    try:
        bench = bars(BENCHMARK)
    except Exception as exc:  # noqa: BLE001 - shown as unknown, never as OK
        return Check("Fiyat verisi", UNKNOWN, f"okunamadı ({type(exc).__name__})")

    if bench.empty:
        return Check("Fiyat verisi", UNKNOWN, "XU100 verisi yok")

    last = bench.index[-1].date()
    expected = due_session(now)  # prices arrive with the 18:30 report (D11)
    behind = sessions_between(last, expected)

    if behind <= 0:
        return Check("Fiyat verisi", OK, f"XU100 son kapanış {_date(last)}")
    return Check("Fiyat verisi", WARN, f"XU100 son kapanış {_date(last)}; {behind} seans geride")


def fundamentals_check() -> Check:
    """Fundamental data (K-48): a fact, not a fault, while the store is empty by design."""

    from core.fundamentals import store

    try:
        from core.market.universe import load_universe

        symbols = load_universe()
    except Exception:  # noqa: BLE001 - the line still shows the store itself
        symbols = None
    text = store.status_text(symbols=symbols)
    return Check("Temel veri", UNKNOWN if text.startswith("okunamadı") else INFO, text)


def calendar_check(now: datetime) -> Check:
    until = covered_until()
    upcoming = [h for d, h in sorted(holidays().items()) if now.date() <= d <= now.date() + timedelta(days=14)]
    soon = "; yaklaşan: " + ", ".join(
        f"{h.day:%d.%m} {h.name}{' (yarım gün)' if h.kind == 'half' else ''}" for h in upcoming
    ) if upcoming else ""

    if until is None or until < now.year:
        return Check("Tatil takvimi", UNKNOWN, f"{now.year} yılı tatilleri data/bist_holidays.csv'de yok")
    if until == now.year and now.month == 12:
        return Check("Tatil takvimi", WARN, f"{until + 1} tatilleri henüz eklenmedi{soon}")
    return Check("Tatil takvimi", OK, f"{until} sonuna kadar{soon}")


PYTHON_END_OF_LIFE = date(2027, 10, 31)  # Python 3.11 security support ends (python.org)
REVIEW_NOTICE = timedelta(days=14)  # Borsa İstanbul announces each quarterly review ~10 days ahead
EOL_NOTICE = timedelta(days=120)


def _next_quarter(day: date) -> date:
    month = (day.month - 1) // 3 * 3 + 4
    return date(day.year + (month > 12), (month - 1) % 12 + 1, 1)


def _last_review(path: Path | None = None) -> date | None:
    """Start of the quarter of the latest quarterly BIST 100 review in data/bist100_changes.csv. A review takes
    effect on the quarter's first session (e.g. 2027-01-04), so the first week of Jan/Apr/Jul/Oct counts."""

    try:
        with open(path or DATA_DIR / "bist100_changes.csv", encoding="utf-8-sig", newline="") as fh:
            days = [date.fromisoformat(r["effective_date"]) for r in csv.DictReader(fh)]
    except (OSError, ValueError, KeyError):
        return None
    reviews = [date(d.year, d.month, 1) for d in days if d.month in (1, 4, 7, 10) and d.day <= 7]
    return max(reviews) if reviews else None


def maintenance_check(now: datetime, last_review: date | None = None) -> Check:
    """CHARTER J3: the quarterly BIST 100 review and the Python version, announced before they expire."""

    name = "Bakım takvimi"
    last_review = last_review or _last_review()
    if last_review is None:
        return Check(name, UNKNOWN, "bist100_changes.csv okunamadı")
    today = now.date()
    review = _next_quarter(last_review)
    notes, state = [], OK
    if today >= review:
        state = WARN
        notes.append(f"BIST 100 {review:%d.%m.%Y} dönem değişiklikleri girilmedi: data/bist100_changes.csv ve "
                     "universe.csv (Borsa İstanbul duyurusu)")
    elif review - today <= REVIEW_NOTICE:
        state = INFO
        notes.append(f"BIST 100 dönem değişikliği {review:%d.%m.%Y}'de; duyuru çıkınca bist100_changes.csv'ye girilecek")
    else:
        notes.append(f"sonraki BIST 100 dönemi {review:%d.%m.%Y}")
    if PYTHON_END_OF_LIFE - today <= EOL_NOTICE:
        state = WARN
        notes.append(f"Python 3.11 desteği {PYTHON_END_OF_LIFE:%d.%m.%Y}'de bitiyor: yeni sürüme geçiş planlanmalı")
    return Check(name, state, "; ".join(notes))


def signal_check(path: Path | str | None = None, now: datetime | None = None) -> Check:
    path = Path(path or SIGNAL_LOG_FILE)
    if not path.exists():
        return Check("Canlı ölçüm kaydı", UNKNOWN, "signal_log.csv yok")

    try:
        audit = audit_log(path, now)
    except (OSError, csv.Error) as exc:
        return Check("Canlı ölçüm kaydı", WARN, f"okunamadı ({exc})")

    if not audit.days:
        return Check("Canlı ölçüm kaydı", WARN if audit.problems else UNKNOWN, audit.text())
    return Check("Canlı ölçüm kaydı", WARN if audit.problems else OK, audit.text())


def equity_check(path: Path | str | None = None) -> Check:
    path = Path(path or EQUITY_LOG_FILE)
    if not path.exists():
        return Check("Sanal hesap kaydı", UNKNOWN, "equity_log.csv yok")

    try:
        df = pd.read_csv(path)
        paper = df[df["account"] == "paper"]
        last = paper.iloc[-1]
    except Exception as exc:  # noqa: BLE001 - shown as a problem, never as OK
        return Check("Sanal hesap kaydı", WARN, f"okunamadı ({type(exc).__name__})")

    return Check(
        "Sanal hesap kaydı", OK, f"{_date(date.fromisoformat(last['date']))}: {tr(float(last['value']))} TL"
    )


PULL_MARKER = "pulled.txt"  # written by scripts/pull_backups after copying the backups off a server
PULL_MAX_AGE = timedelta(days=8)
SYNCED_FOLDERS = ("onedrive", "dropbox", "google drive", "googledrive", "icloud")


def _device(path: Path) -> int:
    return os.stat(path).st_dev


def _location_warning(target: Path, data_dir: Path) -> str | None:
    """A backup lost together with the data is not a backup: same folder tree or same disk."""

    try:
        target, data_dir = target.resolve(), data_dir.resolve()
    except OSError:
        return None
    if target == data_dir or data_dir in target.parents:
        return "proje klasöründe; disk arızasında verilerle birlikte kaybolur. .env'de BACKUP_DIR'i OneDrive'a veya başka bir diske ayarlayın"
    if any(name in part.lower() for part in target.parts for name in SYNCED_FOLDERS):
        return None  # synced to the cloud: a copy lives off this disk
    try:
        same = _device(target) == _device(data_dir)
    except OSError:
        return None
    if same:
        return "verilerle aynı diskte; disk arızasında ikisi birlikte kaybolur. BACKUP_DIR'i OneDrive'a veya başka bir diske ayarlayın"
    return None


def backup_check(now: datetime, target: Path | None = None, data_dir: Path | None = None) -> Check:
    from core.backup import backup_dir
    from core.backup import daily_backups as list_backups

    target = Path(target or backup_dir())
    try:
        backups = list_backups(target)
    except OSError as exc:
        return Check("Yedek", UNKNOWN, f"klasör okunamadı ({exc})")

    if not backups:
        return Check("Yedek", UNKNOWN, f"yedek yok ({target})")

    last = backups[-1]
    taken = datetime.fromtimestamp(last.stat().st_mtime, tz=ISTANBUL)
    text = f"{last.name} ({taken:%d.%m %H:%M})"

    if now - taken > BACKUP_CRIT_AGE:
        return Check("Yedek", CRIT, f"{text}; {(now - taken).days} gündür yeni yedek yok")
    if now - taken > BACKUP_MAX_AGE:
        return Check("Yedek", WARN, f"{text}; {(now - taken).days} gündür yeni yedek yok")
    where = _location_warning(target, Path(data_dir or DATA_DIR))
    if where:
        marker = target / PULL_MARKER
        if not marker.exists():
            return Check("Yedek", WARN, f"{text}; yedek {where}")
        try:
            pulled = datetime.fromisoformat(marker.read_text(encoding="utf-8").strip())
            if pulled.tzinfo is None:
                pulled = pulled.replace(tzinfo=ISTANBUL)
        except (OSError, ValueError):
            return Check("Yedek", WARN, f"{text}; {PULL_MARKER} okunamadı, yedeğin başka yere alındığı doğrulanamıyor")
        if now - pulled > PULL_MAX_AGE:
            return Check("Yedek", WARN, f"{text}; yedek {(now - pulled).days} gündür sunucudan alınmadı "
                                        "(scripts/pull_backups)")
        return Check("Yedek", OK, f"{text}; PC'ye alındı {pulled:%d.%m %H:%M}")
    return Check("Yedek", OK, text)


DB_TIMEOUT = 30  # seconds to wait for a writer before reporting the store as locked


def database_check(db: Path | None = None) -> Check:
    import sqlite3

    db = Path(db or MARKET_DB)
    if not db.exists():
        return Check("Fiyat veritabanı", UNKNOWN, f"{db.name} yok")
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=DB_TIMEOUT)
        try:
            result = conn.execute("PRAGMA quick_check").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc):  # another process is writing; temporary, the data is not damaged
            return Check("Fiyat veritabanı", WARN, f"kilitli, kontrol edilemedi ({exc}); başka bir işlem yazıyor olabilir")
        return Check("Fiyat veritabanı", CRIT, f"açılamadı ({exc})")
    except sqlite3.Error as exc:
        return Check("Fiyat veritabanı", CRIT, f"açılamadı ({exc})")
    if result != "ok":
        return Check("Fiyat veritabanı", CRIT, f"bütünlük hatası: {result}")
    return Check("Fiyat veritabanı", OK, f"bütünlük ok ({db.stat().st_size / 1e6:.0f} MB)")


def disk_check(folder: Path | None = None) -> Check:
    import shutil

    folder = Path(folder or DATA_DIR)
    try:
        free = shutil.disk_usage(folder).free
    except OSError as exc:
        return Check("Disk", UNKNOWN, f"okunamadı ({exc})")
    text = f"{free / 1e9:.1f} GB boş"
    if free < DISK_CRIT:
        return Check("Disk", CRIT, f"{text}; yedek ve veri yazılamayabilir")
    if free < DISK_WARN:
        return Check("Disk", WARN, text)
    return Check("Disk", OK, text)


def write_heartbeat(path: Path | None = None, now: datetime | None = None) -> None:
    live = path is None
    path = Path(path or HEARTBEAT_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = now or now_istanbul()
    path.write_text(now.isoformat(timespec="seconds"), encoding="utf-8")
    if live:  # the history behind the "bot ayakta kalma" objective (core/reports/slo.py)
        from core.reports.slo import record_heartbeat

        try:
            record_heartbeat(now=now)
        except OSError:
            logger.exception("Heartbeat history not written")


def bot_check(now: datetime, path: Path | None = None) -> Check:
    path = Path(path or HEARTBEAT_FILE)
    if not path.exists():
        return Check("Telegram botu", UNKNOWN, "yaşam sinyali yok (bot v0.37.0 öncesi ya da hiç başlamadı)")
    try:
        beat = datetime.fromisoformat(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError) as exc:
        return Check("Telegram botu", UNKNOWN, f"yaşam sinyali okunamadı ({exc})")
    age = now - beat
    if age > HEARTBEAT_STALE:
        hours = age.total_seconds() / 3600
        return Check("Telegram botu", CRIT, f"{hours:.1f} saattir yaşam sinyali yok (son {beat:%d.%m %H:%M}); "
                                            "komutlar ve 20:00 kontrolü çalışmıyor")
    return Check("Telegram botu", OK, f"çalışıyor (son sinyal {beat:%H:%M})")


def _personal_readers() -> dict:
    from core.alerts import levels
    from core.alerts.log import open_alerts
    from core.screen import command as screen
    from core.fundamentals import store as fundamentals
    from core.screen import subscriptions, virtual
    from core.ledger import load_ledger
    from core.ledger.paper import load_orders
    from core.reports.daily import read_equity
    from core.watchlist import repository

    return {
        LEDGER_FILE: load_ledger,
        PAPER_ORDERS_FILE: load_orders,
        EQUITY_LOG_FILE: lambda p: read_equity(p, "paper"),
        ALERTS_LOG_FILE: open_alerts,
        PRICE_ALARMS_FILE: levels.active,
        SCREENS_FILE: screen.load_saved,
        SCREEN_SUBSCRIPTIONS_FILE: subscriptions.active,
        SCREEN_VIRTUAL_FILE: virtual.books,
        FUNDAMENTALS_FILE: fundamentals.load,
        repository.WATCHLIST_FILE: lambda p: repository.load_watchlist(),
    }


def personal_files_check(readers: dict | None = None) -> Check:
    """Every personal file must be readable to the last line; a damaged one is named with its line."""

    from core.infrastructure.exceptions import PersonalFileError

    readers = readers if readers is not None else _personal_readers()
    problems, checked = [], 0
    for path, read in readers.items():
        path = Path(path)
        if not path.exists():
            continue
        checked += 1
        try:
            read(path)
        except PersonalFileError as exc:
            problems.append(str(exc))
        except Exception as exc:  # noqa: BLE001 - e.g. an impossible ledger history; shown, not hidden
            problems.append(f"{path.name}: {exc}")
    if problems:
        return Check("Kişisel dosyalar", CRIT, " | ".join(problems))
    return Check("Kişisel dosyalar", OK, f"{checked} dosya sonuna kadar okundu")


SCHEMAS = {
    LEDGER_FILE: ({"id", "date", "account", "symbol", "side", "quantity", "price", "fee", "note"},),
    PAPER_ORDERS_FILE: ({"id", "created_at", "symbol", "side", "quantity", "status", "fill_date", "fill_price",
                         "note"},),
    SIGNAL_LOG_FILE: ({"logged_at", "source", "symbol", "score", "view", "data_date", "price", "details"},),
    EQUITY_LOG_FILE: ({"date", "account", "value", "cash", "invested", "positions"},),
    PRICE_ALARMS_FILE: ({"id", "at", "symbol", "direction", "level", "event", "close"},),
    SCREENS_FILE: ({"at", "name", "criteria"},),
    SCREEN_SUBSCRIPTIONS_FILE: ({"at", "chat", "name", "action"},),
    SCREEN_VIRTUAL_FILE: ({"at", "name", "criteria", "action"},),
    FUNDAMENTALS_FILE: ({"symbol", "period_end", "published_at", "item", "value", "unit", "consolidated",
                         "inflation_adjusted", "source", "recorded_at"},),
}


def schema_check(schemas: dict | None = None) -> Check:
    """Every personal file must have at least the columns this version reads (extra columns are fine)."""

    schemas = schemas or SCHEMAS
    problems, seen = [], 0
    for path, (required,) in schemas.items():
        path = Path(path)
        if not path.exists():
            continue
        seen += 1
        try:
            with open(path, encoding="utf-8-sig", newline="") as fh:
                header = set(next(csv.reader(fh), []))
        except (OSError, UnicodeDecodeError) as exc:
            problems.append(f"{path.name} okunamadı ({exc})")
            continue
        missing = required - header
        if missing:
            problems.append(f"{path.name} eksik sütun: {', '.join(sorted(missing))}")
    if problems:
        return Check("Veri şeması", CRIT, "; ".join(problems))
    if not seen:
        return Check("Veri şeması", UNKNOWN, "kişisel dosya yok")
    return Check("Veri şeması", OK, f"{seen} dosya bu sürümle uyumlu")


def research_check(now: datetime, get=None) -> Check:
    """Last GitHub research run (public API, no token)."""

    try:
        get = get or _http_get or __import__("httpx").get
        response = get(RESEARCH_API, params={"per_page": 5}, timeout=10)
        response.raise_for_status()
        runs = [r for r in response.json().get("workflow_runs", []) if r.get("status") == "completed"]
    except Exception as exc:  # noqa: BLE001 - offline or API change: unknown, never OK
        return Check("GitHub araştırması", UNKNOWN, f"sorgulanamadı ({type(exc).__name__})")
    if not runs:
        return Check("GitHub araştırması", UNKNOWN, "tamamlanmış çalışma yok")
    last = runs[0]
    started = datetime.fromisoformat(last["run_started_at"].replace("Z", "+00:00")).astimezone(ISTANBUL)
    text = f"son çalışma {started:%d.%m %H:%M}: {last.get('conclusion')}"
    if last.get("conclusion") != "success":
        return Check("GitHub araştırması", WARN, f"{text} (Actions sekmesinden bakın)")
    if now - started > RESEARCH_MAX_AGE:
        return Check("GitHub araştırması", WARN, f"{text}; haftalık çalışma gecikti")
    return Check("GitHub araştırması", OK, text)


def monitoring_check(now: datetime, state_path: Path | None = None) -> Check:
    """Outside monitoring (OPERATIONS §7): addresses set, last pings delivered. Never shows an address."""

    from core.infrastructure import ping

    name = "Dışarıdan izleme"
    have = {env: bool(ping.address(env)) for env in (ping.REPORT_ENV, ping.BOT_ENV)}
    if not any(have.values()):
        return Check(name, INFO, "kurulmadı (isteğe bağlı): .env'de HC_REPORT_URL ve HC_BOT_URL yok; OPERATIONS §7")
    missing = [env for env, ok in have.items() if not ok]
    if missing:
        return Check(name, WARN, f"{', '.join(missing)} .env'de yok; iki adres de gerekli (OPERATIONS §7)")
    malformed = [f"{env} biçimi hatalı: {why}" for env in have if (why := ping.address_problem(env))]
    if malformed:
        return Check(name, WARN, "; ".join(malformed) + " (OPERATIONS §7)")

    pings = ping.last_pings(state_path)
    problems, parts = [], []
    bot = pings.get(ping.BOT_ENV)
    if not bot:
        problems.append("bot sinyali yok (adres girildikten sonra bot yeniden başlatılmalı)")
    else:
        at = datetime.fromisoformat(bot["at"])
        if not bot.get("ok"):
            problems.append(f"son bot sinyali ulaşmadı ({at:%d.%m %H:%M})")
        elif now - at > BOT_PING_STALE:
            problems.append(f"son bot sinyali {at:%d.%m %H:%M} (20 dakikadan eski)")
        else:
            parts.append(f"bot sinyali {at:%H:%M}")
    report = pings.get(ping.REPORT_ENV)
    if not report:
        parts.append("rapor sinyali henüz yok (ilk 18:30 raporundan sonra gelir)")
    else:
        at = datetime.fromisoformat(report["at"])
        if not report.get("ok"):
            problems.append(f"son rapor sinyali ulaşmadı ({at:%d.%m %H:%M})")
        else:
            parts.append(f"rapor sinyali {at:%d.%m %H:%M}" + (" (/fail: rapor gitmedi)" if report.get("fail") else ""))
    if problems:
        return Check(name, WARN, "; ".join(problems + parts))
    return Check(name, OK, "açık; " + ", ".join(parts))


def weekly_summary(day: date, checks: list[Check], runs_path: Path | str | None = None) -> str:
    """Friday report: reports sent this week (Monday to `day`), open problems, backup, monitoring.
    `day` is the report being built, so it counts as sent."""

    from core.market.calendar import is_session_day

    monday = day - timedelta(days=day.weekday())
    weekdays = [monday + timedelta(days=i) for i in range((day - monday).days + 1)]
    sessions = [d for d in weekdays if is_session_day(d)]
    closed = [d for d in weekdays if not is_session_day(d)]
    sent = {r.data_day for r in run_log.read_runs(runs_path) if r.status == run_log.SENT} | {day.isoformat()}
    missing = [d for d in sessions if d.isoformat() not in sent]

    reports = f"rapor {len(sessions) - len(missing)}/{len(sessions)} seans"
    notes = ([f"eksik: {', '.join(f'{d:%d.%m}' for d in missing)}"] if missing else []) + (
        [f"tatil: {', '.join(f'{d:%d.%m}' for d in closed)}"] if closed else [])
    if notes:
        reports += f" ({'; '.join(notes)})"
    problems = [c.name for c in checks if c.state in (WARN, CRIT)]
    by_name = {c.name: c for c in checks}
    backup = by_name.get("Yedek")
    monitor = by_name.get("Dışarıdan izleme")
    monitor_text = {INFO: "kurulmadı", OK: "açık", None: "?"}.get(monitor.state if monitor else None, "sorunlu")
    return " · ".join([
        f"🩺 Bu hafta sistem: {reports}",
        f"açık uyarı: {', '.join(problems)}" if problems else "açık uyarı yok",
        f"yedek {backup.state if backup else UNKNOWN}",
        f"izleme: {monitor_text}",
    ])


def verdict(checks: list[Check]) -> str:
    states = [c.state for c in checks]
    if CRIT in states:
        return f"{CRIT} KRİTİK: {states.count(CRIT)} açık kritik sorun"
    if WARN in states:
        return f"{WARN} UYARI: dikkat gereken bileşen var"
    if UNKNOWN in states:
        return f"{UNKNOWN} BİLİNMİYOR: bazı bileşenler doğrulanamadı"
    return f"{OK} SAĞLIKLI: tüm kontroller geçti"


def health_checks(now: datetime | None = None, bars=adjusted_bars, online: bool = True) -> list[Check]:
    now = now or now_istanbul()
    checks = [
        bot_check(now),
        report_check(now),
        price_check(now, bars),
        database_check(),
        signal_check(now=now),
        equity_check(),
        schema_check(),
        personal_files_check(),
        backup_check(now),
        disk_check(),
        calendar_check(now),
        fundamentals_check(),
        maintenance_check(now),
        monitoring_check(now),
    ]
    if online:
        checks.append(research_check(now))
    return checks


def health_report(now: datetime | None = None, bars=adjusted_bars) -> str:
    now = now or now_istanbul()
    checks = health_checks(now, bars)
    try:
        from core.reports import slo

        objectives = ["", *slo.lines(slo.measure(now))]
    except Exception as exc:  # noqa: BLE001 - /durum must still answer
        logger.exception("SLO measurement failed")
        objectives = ["", f"{UNKNOWN} SLO ölçülemedi: {type(exc).__name__}"]

    return "\n".join([
        f"🩺 QuantBIST v{__version__} durum – {now:%d.%m.%Y %H:%M}",
        verdict(checks),
        "",
        *(c.line() for c in checks),
        *objectives,
        "",
        "Windows görevi buradan görülemez; çalışması logs/runs.csv kayıtlarından izlenir.",
    ])


def main(argv: list[str] | None = None) -> int:
    """python -m core.reports.health            the /durum text
       python -m core.reports.health --heartbeat exit 0 if the bot wrote its heartbeat recently (Docker)"""

    import argparse

    from core.infrastructure.console import utf8_output

    utf8_output()  # Windows console / redirected output is cp1254
    parser = argparse.ArgumentParser(description="QuantBIST health")
    parser.add_argument("--heartbeat", action="store_true", help="exit 1 when the bot heartbeat is missing or old")
    args = parser.parse_args(argv)
    if args.heartbeat:
        check = bot_check(now_istanbul())
        print(check.line())
        return 0 if check.state == OK else 1
    print(health_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Check", "LABELS", "due_session", "health_checks", "health_report", "write_heartbeat"]
