"""
QuantBIST
Daily after-close report.

    python -m core.reports.daily             # update prices, build, print
    python -m core.reports.daily --send      # ... and send to Telegram
    python -m core.reports.daily --no-update # use stored prices only

Steps, in order:
1. update the price store (the only network step besides --send)
2. fill pending paper orders at the next session's open
3. value both accounts and record today's value in data/equity_log.csv
4. evaluate risk alerts and record changes in data/alerts_log.csv
5. write the report: market, accounts, new / escalated / closed alerts, data notes

Nothing here gives buy or sell advice.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from core.alerts import evaluate_account, evaluate_position, update_alert_log
from core.alerts.portfolio import evaluate_portfolio, portfolio_risk
from core.config import alerts as alert_cfg
from core.config.paths import ALERTS_LOG_FILE, EQUITY_LOG_FILE, LEDGER_FILE, PAPER_ORDERS_FILE
from core.config.trading import ACCOUNTS
from core.infrastructure.logger import get_logger
from core.ledger import cash_balance, load_ledger, open_positions
from core.ledger.paper import fill_pending
from core.market import store
from core.market.calendar import (
    drop_open_candle,
    holiday,
    is_session_day,
    last_final_session_date,
    now_istanbul,
)
from core.market.corrections import clean, drop_cancelled_sessions, load_corporate_actions
from core.market.universe import BENCHMARK, load_universe
from core.reports.runs import ReportBusy, already_sent, record_run, report_lock

logger = get_logger(__name__)

ACCOUNT_NAMES = {"real": "Gerçek hesap", "paper": "Sanal hesap"}
DISCLAIMER = "Bilgi amaçlıdır, yatırım tavsiyesi değildir. Bot AL/SAT önerisi vermez."
UNCONFIRMED_WORDS = ("teyit", "doğrulanmadı")


@dataclass
class Paths:
    ledger: Path = LEDGER_FILE
    orders: Path = PAPER_ORDERS_FILE
    alerts: Path = ALERTS_LOG_FILE
    equity: Path = EQUITY_LOG_FILE


def raw_bars(symbol: str) -> pd.DataFrame:
    """Final raw candles: share prices as traded (ledger quantities match these)."""

    return drop_open_candle(drop_cancelled_sessions(store.read(symbol)))


def adjusted_bars(symbol: str) -> pd.DataFrame:
    """Final candles with corporate actions applied (indicators need continuity)."""

    return drop_open_candle(clean(store.read(symbol), symbol))


def tr(x: float, decimals: int = 0) -> str:
    """Turkish number format: 1.234.567,89"""

    text = f"{x:,.{decimals}f}"
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def pct(x: float, decimals: int = 1) -> str:
    return f"{'+' if x >= 0 else '-'}%{tr(abs(x) * 100, decimals)}"


def unrecorded_actions(position, entries, actions) -> list[str]:
    """Corporate actions on the symbol after the entry, without a bonus/rights ledger row after them."""

    out = []
    for a in actions:
        if a.symbol != position.symbol or position.opened is None or a.ex_date <= position.opened:
            continue
        recorded = any(
            e.symbol == position.symbol and e.account == position.account
            and e.side in ("bonus", "rights") and e.date >= a.ex_date - timedelta(days=30)
            for e in entries
        )
        if not recorded and a.kind in ("bonus", "rights"):
            out.append(f"{a.ex_date:%d.%m.%Y} {a.note.split(';')[0]}")
    return out


# ---------------------------------------------------------------------------
# Equity log
# ---------------------------------------------------------------------------

EQUITY_FIELDS = ("date", "account", "value", "cash", "invested", "positions")


def read_equity(path: Path, account: str) -> pd.Series:
    if not path.exists():
        return pd.Series(dtype=float)
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[df["account"] == account]
    return df.set_index("date")["value"].astype(float).sort_index()


def record_equity(path: Path, day: date, account: str, value: float, cash: float, invested: float, n: int):
    """One row per (date, account); a rerun on the same day replaces that row."""

    rows = []
    if path.exists():
        with open(path, encoding="utf-8", newline="") as fh:
            rows = [r for r in csv.DictReader(fh) if not (r["date"] == day.isoformat() and r["account"] == account)]
    rows.append(
        {"date": day.isoformat(), "account": account, "value": f"{value:.2f}", "cash": f"{cash:.2f}",
         "invested": f"{invested:.2f}", "positions": n}
    )
    rows.sort(key=lambda r: (r["date"], r["account"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, EQUITY_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Market section
# ---------------------------------------------------------------------------


def market_section(frames: dict[str, pd.DataFrame], bench: pd.DataFrame) -> list[str]:
    lines = ["📊 Piyasa"]
    if len(bench) >= 200:
        close = float(bench["close"].iloc[-1])
        sma200 = float(bench["close"].tail(200).mean())
        change = float(bench["close"].iloc[-1] / bench["close"].iloc[-2] - 1)
        side = "üstünde" if close > sma200 else "altında"
        lines.append(
            f"XU100 {tr(close)} ({pct(change, 2)}); 200 günlük ortalamanın %{tr(abs(close / sma200 - 1) * 100, 1)} {side}"
        )
    above50 = above200 = counted = 0
    for df in frames.values():
        if len(df) < 200:
            continue
        counted += 1
        c = df["close"]
        above50 += c.iloc[-1] > c.tail(50).mean()
        above200 += c.iloc[-1] > c.tail(200).mean()
    if counted:
        lines.append(
            f"Katılım ({counted} hisse): 50 günlük ortalamanın üstünde olan oranı %{above50 / counted * 100:.0f}, "
            f"200 günlük için %{above200 / counted * 100:.0f}"
        )
    return lines


def liquidity_ranks(frames: dict[str, pd.DataFrame], days: int = 60) -> dict[str, int]:
    turnover = {
        s: float((df["close"] * df["volume"].where(df["volume"] > 0)).tail(days).median())
        for s, df in frames.items()
        if not df.empty
    }
    ordered = sorted((v, s) for s, v in turnover.items() if not pd.isna(v))
    return {s: rank for rank, (_, s) in enumerate(reversed(ordered), start=1)}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass
class DailyResult:
    day: date
    text: str
    events: list = field(default_factory=list)
    fills: list = field(default_factory=list)
    # built | sent | skipped (second run) | holiday (no session today) | stale (no new candle)
    status: str = "built"
    note: str = ""


def build_daily(paths: Paths | None = None, universe: list[str] | None = None, today: date | None = None) -> DailyResult:
    paths = paths or Paths()
    universe = universe or load_universe()

    fills = fill_pending(raw_bars, paths.orders, paths.ledger)
    entries = load_ledger(paths.ledger)

    frames = {s: adjusted_bars(s) for s in universe}
    frames = {s: df for s, df in frames.items() if not df.empty}
    bench = adjusted_bars(BENCHMARK)
    day = (bench.index[-1].date() if not bench.empty else None) or today or last_final_session_date()
    ranks = liquidity_ranks(frames)
    actions = load_corporate_actions()
    unconfirmed = {
        a.symbol: a.note
        for a in actions
        if any(w in a.note.lower() for w in UNCONFIRMED_WORDS)
    }

    lines = [f"🗓 QuantBIST günlük rapor – {day:%d.%m.%Y} kapanışı", ""]
    lines += market_section(frames, bench)

    alerts = []
    for account in ACCOUNTS:
        positions = open_positions(entries, account)
        if account == "real" and not positions:
            continue
        rows = []
        invested = 0.0
        for p in positions:
            raw = raw_bars(p.symbol)
            price = float(raw["close"].iloc[-1]) if not raw.empty else float("nan")
            value = p.quantity * price
            invested += 0 if pd.isna(value) else value
            rows.append((p, price, value))
        cash = cash_balance(entries, account) if account == "paper" else 0.0
        total = cash + invested
        if positions or account == "paper":
            record_equity(paths.equity, day, account, total, cash, invested, len(positions))

        lines += ["", f"💼 {ACCOUNT_NAMES[account]}"]
        if account == "paper":
            lines.append(f"Değer {tr(total)} TL (nakit {tr(cash)} TL, hisse {tr(invested)} TL)")
        else:
            lines.append(f"Hisse değeri {tr(invested)} TL")
        equity = read_equity(paths.equity, account)
        if len(equity) >= 2:
            lines.append(f"Günlük değişim {pct(equity.iloc[-1] / equity.iloc[-2] - 1, 2)}")
        for p, price, value in rows:
            pnl = value - p.cost
            ret = pnl / p.cost if p.cost else 0.0
            lines.append(
                f"  {p.symbol.removesuffix('.IS')}: {tr(p.quantity)} adet × {tr(price, 2)} = {tr(value)} TL "
                f"(maliyet {tr(p.average_cost, 2)}; {'+' if pnl >= 0 else '-'}{tr(abs(pnl))} TL / {pct(ret)})"
            )
            alerts += evaluate_position(
                account, p.symbol, p.quantity, p.opened, adjusted_bars(p.symbol),
                account_value=total if total > 0 else None,
                liquidity_rank=ranks.get(p.symbol),
                unconfirmed_action=unconfirmed.get(p.symbol),
                reference_day=day,
                unrecorded_actions=unrecorded_actions(p, entries, actions),
            )
        if not positions:
            lines.append("  Açık pozisyon yok.")
        else:
            risk = portfolio_risk(
                {p.symbol: value for p, _, value in rows},
                {p.symbol: adjusted_bars(p.symbol) for p, _, _ in rows},
                total,
            )
            lines.append(risk.line())
            alerts += evaluate_portfolio(account, risk, day)
        alerts += evaluate_account(account, equity)

    events = update_alert_log(alerts, day, paths.alerts)
    lines += ["", "⚠️ Risk uyarıları"]
    if not alerts and not events:
        lines.append("Uyarı yok.")
    for event, item in events:
        if event == "close":
            lines.append(f"  ✅ kapandı: {item['symbol'].removesuffix('.IS')} {item['rule']}")
        else:
            prefix = "🆕" if event == "open" else "⬆️"
            lines.append(f"  {prefix} {item.line()}")
    still = [a for a in alerts if a.key not in {i.key for e, i in events if e != 'close'}]
    if still:
        lines.append(f"  Süren uyarılar: {len(still)} (/alerts ile listelenir)")

    if fills:
        lines += ["", "🧾 Sanal emirler"]
        for o in fills:
            if o.status == "filled":
                verb = "alındı" if o.side == "buy" else "satıldı"
                cost = f", açılış {tr(o.fill_open, 2)} + kayma, komisyon {tr(o.fee, 2)} TL" if o.fill_open else ""
                lines.append(
                    f"  #{o.id} {o.symbol.removesuffix('.IS')} {tr(o.quantity)} adet, {tr(o.fill_price, 2)} TL'den "
                    f"{verb} ({o.fill_date:%d.%m.%Y}{cost})"
                )
                if o.fill_log:
                    lines.append(f"     {o.fill_log}")
            else:
                lines.append(f"  #{o.id} {o.symbol.removesuffix('.IS')} reddedildi: {o.note}")

    stale = [s for s, df in frames.items() if (pd.Timestamp(day) - df.index[-1]).days > alert_cfg.STALE_DAYS]
    missing = [s for s in universe if s not in frames]
    if stale or missing:
        lines += ["", "🔎 Veri notları"]
        if missing:
            lines.append(f"  Verisi olmayan: {', '.join(s.removesuffix('.IS') for s in missing)}")
        if stale:
            lines.append(f"  Güncel olmayan: {', '.join(s.removesuffix('.IS') for s in stale)}")

    lines += ["", DISCLAIMER]
    return DailyResult(day, "\n".join(lines), events, fills)


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------


def split_text(text: str, limit: int = 4000) -> list[str]:
    parts, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit and current:
            parts.append(current)
            current = ""
        current += line
    if current:
        parts.append(current)
    return parts


SEND_ATTEMPTS = 3
SEND_PAUSES = (5, 20)  # seconds between attempts


def send_telegram(text: str, token: str, chat_id: int, post=None, sleep=None) -> None:
    """
    Send with the Bot HTTP API. A network error, a 5xx or a 429 is retried
    (SEND_ATTEMPTS times); a 4xx such as a wrong token is not. Each part is
    retried on its own, so a part that went out is never sent twice.
    `post` and `sleep` are injectable for tests.
    """

    import time

    import httpx

    post = post or httpx.post
    sleep = sleep or time.sleep
    retryable = (ConnectionError, OSError, TimeoutError, httpx.TransportError)
    for part in split_text(text):
        for attempt in range(SEND_ATTEMPTS):
            try:
                response = post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": part},
                    timeout=30,
                )
                status = getattr(response, "status_code", 200)
                if status == 429 or status >= 500:
                    raise ConnectionError(f"Telegram HTTP {status}")
                response.raise_for_status()
                break
            except retryable as exc:
                if attempt == SEND_ATTEMPTS - 1:
                    raise
                logger.warning("Telegram send failed, retrying | %s", exc)
                sleep(SEND_PAUSES[min(attempt, len(SEND_PAUSES) - 1)])


def utf8_output(stream=None) -> None:
    """
    Make printing safe when Windows redirects output to a file: Python then
    uses the ANSI code page (cp1254), which has no emoji and crashed the
    scheduled report before it was sent.
    """

    import sys

    stream = stream or sys.stdout
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def _with_backup_line(text: str) -> str:
    """Back up the personal records; a failed backup is reported, never fatal."""

    from core.backup import create_backup

    try:
        backup = create_backup()
        line = backup.line() if backup else "💾 Yedeklenecek kişisel dosya yok."
    except Exception as exc:  # noqa: BLE001 - the report must still go out
        logger.exception("Backup failed")
        line = f"⚠️ Yedek alınamadı: {exc}"

    weekly = _weekly_backup_check()
    return _before_disclaimer(text, line + (f"\n{weekly}" if weekly else ""))


def _with_health_warnings(text: str) -> str:
    """
    The report runs from the Windows task, so it can see what the bot
    cannot report about itself (the bot being down) and local problems.
    Only problems are added; never fatal.
    """

    from core.reports.health import OK, UNKNOWN, bot_check, database_check, disk_check, schema_check

    try:
        checks = [bot_check(now_istanbul()), database_check(), disk_check(), schema_check()]
        lines = [c.line() for c in checks if c.state not in (OK, UNKNOWN)]
    except Exception as exc:  # noqa: BLE001 - the report must still go out
        logger.exception("Health warnings failed")
        lines = [f"⚠️ Sağlık kontrolü yapılamadı: {exc}"]
    return _before_disclaimer(text, "\n".join(lines)) if lines else text


WEEKLY_BACKUP_DAYS = 6


def _weekly_backup_check(today: date | None = None) -> str:
    """
    Once a week: snapshot the price store and restore the newest backups
    into a temporary folder (the live files are not touched). Never fatal.
    """

    from core.backup import backup_market_db, market_db_backups, test_restore

    today = today or date.today()
    try:
        latest = market_db_backups()[-1:]
        if latest and (today - date.fromisoformat(latest[0].stem[-10:])).days < WEEKLY_BACKUP_DAYS:
            return ""
        backup_market_db()
        checked = test_restore()
        return f"🔁 Haftalık geri yükleme testi başarılı: {len(checked)} dosya okundu (fiyat veritabanı dahil)"
    except Exception as exc:  # noqa: BLE001 - the report must still go out
        logger.exception("Weekly backup check failed")
        return f"⚠️ Haftalık yedek/geri yükleme testi başarısız: {exc}"


def _before_disclaimer(text: str, line: str) -> str:
    head, sep, tail = text.rpartition(DISCLAIMER)
    return f"{head}{line}\n\n{sep}{tail}" if sep else f"{text}\n\n{line}"


FRIDAY = 4


def _with_weekly_line(text: str, day: date) -> str:
    """On Fridays add the live-measurement summary; never fatal."""

    if day.weekday() != FRIDAY:
        return text

    from core.reports.forward import weekly_line

    try:
        return _before_disclaimer(text, weekly_line())
    except Exception:  # noqa: BLE001 - the report must still go out
        logger.exception("Weekly summary failed")
        return text


def _record_scores() -> None:
    """Record every stock's view for the live measurement; never fatal."""

    from core.reports.forward import log_daily_scores

    try:
        written = log_daily_scores(load_universe())
        logger.info("Daily scores recorded | %d stocks", written)
    except Exception:  # noqa: BLE001 - the report must still go out
        logger.exception("Daily score recording failed")


def _notify_failure(error: Exception, log_name: str) -> None:
    """Tell the user in Telegram that the scheduled report did not come out."""

    try:
        from core.infrastructure.settings import require_bot_settings

        s = require_bot_settings()
        send_telegram(
            f"⚠️ QuantBIST günlük rapor hazırlanamadı.\n{type(error).__name__}: {error}\n"
            f"Ayrıntı: {log_name}",
            s.bot_token,
            s.chat_id,
        )
    except Exception:  # noqa: BLE001 - nothing more can be done; the log has it
        logger.exception("Failure notice could not be sent")


def _not_sent_reason(day: date, now=None) -> tuple[str, str]:
    """Why a run found its data day already sent."""

    now = now or now_istanbul()
    today = now.date()
    if not is_session_day(today):
        h = holiday(today)
        return "holiday", h.name if h else "hafta sonu"
    expected = last_final_session_date(now)
    if day < expected:
        return "stale", f"beklenen {expected:%d.%m.%Y} kapanışı, veri {day:%d.%m.%Y}"
    return "skipped", "bu veri günü zaten gönderilmişti"


def _run(args) -> DailyResult:
    with report_lock():
        return _run_locked(args)


def _run_locked(args) -> DailyResult:
    if not args.no_update:
        status = store.update([BENCHMARK, *load_universe()])
        failed = [s for s, v in status.items() if v in ("failed", "empty")]
        if failed:
            logger.warning("Daily update: no data for %s", ", ".join(failed))

    result = build_daily()
    _record_scores()

    if args.send and not args.force and already_sent(result.day):
        # never send the same data day twice; say why in logs/runs.csv
        result.status, result.note = _not_sent_reason(result.day)
        logger.info("Daily report for %s was already sent (%s); not sending again", result.day, result.status)
        return result

    result.text = _with_weekly_line(result.text, result.day)
    result.text = _with_backup_line(result.text)
    result.text = _with_health_warnings(result.text)

    # send first: a problem while printing must never stop the report
    if args.send:
        from core.infrastructure.settings import require_bot_settings

        s = require_bot_settings()
        send_telegram(result.text, s.bot_token, s.chat_id)
        result.status = "sent"
        logger.info("Daily report sent to Telegram | %s", result.day)
    return result


def main(argv: list[str] | None = None) -> int:
    """
    Returns the exit code. With --log-dir the run writes its own dated log
    file (UTF-8): the report, or the full error. This is what the Windows
    scheduled task uses (pythonw.exe has no console to print to).
    """

    import sys
    import traceback
    from datetime import datetime

    utf8_output(sys.stdout)
    utf8_output(sys.stderr)
    parser = argparse.ArgumentParser(description="QuantBIST daily report")
    parser.add_argument("--send", action="store_true", help="send the report to Telegram")
    parser.add_argument("--no-update", action="store_true", help="do not download prices")
    parser.add_argument("--log-dir", default=None, help="write logs/daily_<date>.log here")
    parser.add_argument("--force", action="store_true", help="send even if this data day was already sent")
    args = parser.parse_args(argv)

    started = now_istanbul()

    log_file = None
    if args.log_dir:
        Path(args.log_dir).mkdir(parents=True, exist_ok=True)
        log_file = Path(args.log_dir) / f"daily_{datetime.now():%Y-%m-%d}.log"

    def write_log(text: str) -> None:
        if log_file is not None:
            with open(log_file, "a", encoding="utf-8") as fh:
                fh.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n{text}\n")

    try:
        result = _run(args)
    except ReportBusy as exc:
        # another run is doing the work right now; not a failure
        logger.warning("%s", exc)
        write_log(f"ATLANDI: {exc}")
        record_run(started, "busy", detail=str(exc))
        print(exc)
        return 0
    except Exception as exc:  # noqa: BLE001 - the scheduled run must leave a trace
        error = traceback.format_exc()
        logger.error("Daily report failed\n%s", error)
        write_log("HATA\n" + error)
        record_run(started, "failed", detail=f"{type(exc).__name__}: {exc}")
        print(error, file=sys.stderr)
        if args.send:
            _notify_failure(exc, str(log_file or "logs/quantbist.log"))
        return 1

    record_run(started, result.status, result.day, result.note)
    note = "\n\nTelegram'a gönderildi." if result.status == "sent" else (
        f"\n\nTelegram'a gönderilmedi ({result.status}: {result.note})." if result.note else ""
    )
    write_log(result.text + note)
    print(result.text + note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Paths", "DailyResult", "build_daily", "send_telegram", "split_text", "main"]
