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
import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from core.alerts import evaluate_account, evaluate_position, update_alert_log
from core.alerts.portfolio import evaluate_portfolio, portfolio_risk
from core.config import alerts as alert_cfg
from core.config.paths import ALERTS_LOG_FILE, EQUITY_LOG_FILE, LEDGER_FILE, LOG_DIR, PAPER_ORDERS_FILE
from core.config.trading import ACCOUNTS
from core.infrastructure import ping
from core.infrastructure.console import utf8_output
from core.infrastructure.csvfiles import read_rows
from core.infrastructure.exceptions import PersonalFileError
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
    sessions_between,
)
from core.market.corrections import clean, drop_cancelled_sessions, load_corporate_actions
from core.market.universe import BENCHMARK, load_universe
from core.reports.runs import ReportBusy, already_sent, record_run, report_lock

logger = get_logger(__name__)

ACCOUNT_NAMES = {"real": "Gerçek hesap", "paper": "Sanal hesap"}
DISCLAIMER = "Bilgi amaçlıdır, yatırım tavsiyesi değildir. Bot AL/SAT önerisi vermez."
UNCONFIRMED_WORDS = ("teyit bekl", "teyitsiz", "teyit edilmedi", "doğrulanmadı", "doğrulanacak", "kesinleşmedi")


def corporate_action_problems(problems: list[str]) -> list[str]:
    """Unreadable rows plus the actions skipped because the provider already adjusted them (M15)."""

    from core.market.corrections import double_adjusted

    return problems + sorted(double_adjusted().values())


def is_unconfirmed(note: str) -> bool:
    """A corporate-action note that says it is not confirmed yet (Turkish case folding; validation M11)."""

    text = (note or "").replace("İ", "i").replace("I", "ı").lower()
    return any(w in text for w in UNCONFIRMED_WORDS)


@dataclass
class Paths:
    ledger: Path = LEDGER_FILE
    orders: Path = PAPER_ORDERS_FILE
    alerts: Path = ALERTS_LOG_FILE
    equity: Path = EQUITY_LOG_FILE


def raw_bars(symbol: str) -> pd.DataFrame:
    """
    Final candles without our corporate actions (ledger quantities match these). Not truly as traded
    for old days: Yahoo's series (auto_adjust) already carries its own dividend and split
    adjustments (validation M15 O-3). Today's close is the traded price.
    """

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


def _equity_rows(path: Path) -> list[tuple[int, dict]]:
    rows = read_rows(path, EQUITY_FIELDS)
    for line, r in rows:
        try:
            date.fromisoformat(r["date"])
            float(r["value"])
        except ValueError as exc:
            raise PersonalFileError(path, str(exc), line=line) from exc
    return rows


def read_equity(path: Path, account: str) -> pd.Series:
    rows = [r for _, r in _equity_rows(Path(path)) if r["account"] == account]
    if not rows:
        return pd.Series(dtype=float)
    series = pd.Series({pd.Timestamp(r["date"]): float(r["value"]) for r in rows}, dtype=float)
    series.index.name = "date"
    series.name = "value"
    return series.sort_index()


def performance_index(equity: pd.Series, entries, account: str) -> pd.Series:
    """
    The account's growth with money moved in or out left out (1.0 at the first record).

    The real account's value is the market value of its shares: a buy raises it and a sale
    lowers it with no gain or loss. Between two records (Modified Dietz, weights 1 and 0):
        gain = value now − value at the last record − money put in
        return = gain / (value at the last record + money put in, if positive)
    money put in = what was paid for buys and rights minus what sales and dividends brought
    (after fees). Money put in works from the start of the period, money taken out leaves at
    its end; dividing by the old value alone made a buy day's return explode (validation M14).
    The paper account's value includes its cash, so its trades move nothing in or out.
    """

    if len(equity) < 2:
        return pd.Series(1.0, index=equity.index, dtype=float)
    flows = pd.Series(0.0, index=equity.index)
    if account == "real":
        for e in entries:
            if e.account != account or e.side == "bonus":
                continue
            # trades after the first record, credited to the first record on or after their date
            later = equity.index[equity.index >= pd.Timestamp(e.date)]
            if len(later) and later[0] > equity.index[0]:
                flows[later[0]] += -e.amount
    values = equity.to_numpy(dtype=float)
    growth = [1.0]
    for i in range(1, len(values)):
        previous, flow = values[i - 1], flows.iloc[i]
        base = previous + max(flow, 0.0)
        r = (values[i] - previous - flow) / base if base > 0 else 0.0
        growth.append(growth[-1] * (1 + r))
    return pd.Series(growth, index=equity.index, dtype=float)


def record_equity(path: Path, day: date, account: str, value: float, cash: float, invested: float, n: int):
    """One row per (date, account); a rerun on the same day replaces that row."""

    # a damaged file raises here, before anything is rewritten
    rows = [r for _, r in _equity_rows(path) if not (r["date"] == day.isoformat() and r["account"] == account)]
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


@dataclass
class Holding:
    position: object  # core.ledger.book.Position
    price: float  # last final raw close; NaN when the stock has no price
    price_day: date | None
    value: float  # quantity x price (NaN without a price)


def value_holdings(entries, account: str, bars=None) -> tuple[list[Holding], float]:
    """
    Every open position of an account at its last final raw close, and the invested total
    (positions without a price are left out of the total; the Risk line names them).
    The daily report, /portfolio and the paper order snapshot all value holdings with this.
    """

    bars = bars or raw_bars
    rows, invested = [], 0.0
    for p in open_positions(entries, account):
        raw = bars(p.symbol)
        price = float(raw["close"].iloc[-1]) if not raw.empty else float("nan")
        day = raw.index[-1].date() if not raw.empty else None
        value = p.quantity * price
        invested += 0 if pd.isna(value) else value
        rows.append(Holding(p, price, day, value))
    return rows, invested


def symbols_to_update(paths: Paths | None = None, universe: list[str] | None = None) -> list[str]:
    """
    XU100, the universe, and every stock held or waiting in a paper order: a holding
    outside the BIST 100 list would otherwise keep its old price (and its order never fill).
    """

    from core.ledger.paper import load_orders

    paths = paths or Paths()
    held = [p.symbol for p in open_positions(load_ledger(paths.ledger))]
    ordered = [o.symbol for o in load_orders(paths.orders) if o.status == "pending"]
    from core.market.regime import SECTORS

    return list(dict.fromkeys([BENCHMARK, *(universe or load_universe()), *held, *ordered, *_alarm_symbols(),
                               *_bist100_members(), *SECTORS]))


def _bist100_members() -> list[str]:
    """Today's official BIST 100: /tara scans it (DECISIONS K-36), and 14 members are not in
    data/universe.csv. A membership file problem never stops the update."""

    try:
        from core.market.membership import members_on

        return sorted(f"{code}.IS" for code in members_on(now_istanbul().date()))
    except Exception:  # noqa: BLE001
        logger.exception("BIST 100 membership could not be read")
        return []


def _alarm_symbols() -> list[str]:
    """Stocks with a price alarm need today's close too; a damaged alarm file never stops the update."""

    from core.alerts import levels

    try:
        return [a.symbol for a in levels.active()]
    except Exception:  # noqa: BLE001
        logger.exception("Price alarms could not be read")
        return []


def build_daily(
    paths: Paths | None = None,
    universe: list[str] | None = None,
    today: date | None = None,
    record_alerts: bool = True,
) -> DailyResult:
    """record_alerts=False (/report by hand): alert changes are shown but not written, so the
    scheduled report still announces them."""

    paths = paths or Paths()
    universe = universe or load_universe()
    damaged: list[str] = []  # logs that could not be read or written; the report goes on without them

    def guarded(step, fallback):
        try:
            return step()
        except PersonalFileError as exc:
            note = str(exc)
        except PermissionError as exc:  # Windows: the file is open in another program (e.g. Excel)
            note = (f"{Path(exc.filename or '?').name} kilitli: Excel gibi bir programda açık olabilir. "
                    "Bu çalışmada yazılmadı; dosya kapanınca sonraki çalışma yazar.")
        except OSError as exc:  # e.g. a full disk: sending the report needs no disk, so it still goes out
            import errno

            why = "disk dolu" if exc.errno == errno.ENOSPC else (exc.strerror or type(exc).__name__)
            note = f"{Path(exc.filename or '?').name} yazılamadı: {why}. Sonraki çalışma yazar."
        if note not in damaged:
            damaged.append(note)
        return fallback

    # an order whose fill was booked but not saved is recognised next time (fill_pending is idempotent)
    fills = guarded(lambda: fill_pending(raw_bars, paths.orders, paths.ledger), [])
    entries = load_ledger(paths.ledger)

    frames = {s: adjusted_bars(s) for s in universe}
    frames = {s: df for s, df in frames.items() if not df.empty}
    bench = adjusted_bars(BENCHMARK)
    day = (bench.index[-1].date() if not bench.empty else None) or today or last_final_session_date()
    ranks = liquidity_ranks(frames)
    action_problems: list[str] = []
    actions = load_corporate_actions(problems=action_problems)
    action_problems = corporate_action_problems(action_problems)
    unconfirmed = {
        a.symbol: a.note
        for a in actions
        if is_unconfirmed(a.note)
    }

    lines = [f"🗓 QuantBIST günlük rapor – {day:%d.%m.%Y} kapanışı", ""]
    lines += market_section(frames, bench)
    alerts = []
    for account in ACCOUNTS:
        positions = open_positions(entries, account)
        if account == "real" and not positions:
            continue
        holdings, invested = value_holdings(entries, account)
        rows = [(h.position, h.price, h.value) for h in holdings]
        cash = cash_balance(entries, account) if account == "paper" else 0.0
        total = cash + invested
        if positions or account == "paper":
            guarded(lambda: record_equity(paths.equity, day, account, total, cash, invested, len(positions)), None)

        lines += ["", f"💼 {ACCOUNT_NAMES[account]}"]
        if account == "paper":
            lines.append(f"Değer {tr(total)} TL (nakit {tr(cash)} TL, hisse {tr(invested)} TL)")
        else:
            lines.append(f"Hisse değeri {tr(invested)} TL")
        equity = guarded(lambda: read_equity(paths.equity, account), pd.Series(dtype=float))
        growth = performance_index(equity, entries, account)  # buys and sales are not gains or losses
        if len(growth) >= 2:
            change = pct(growth.iloc[-1] / growth.iloc[-2] - 1, 2)
            before, last = growth.index[-2].date(), growth.index[-1].date()
            gap = sessions_between(before, last)
            # a missing day (PC off) makes the change cover several sessions: say since when
            lines.append(f"Günlük değişim {change}" if gap <= 1
                         else f"{before:%d.%m} kaydından bu yana değişim {change} ({gap} seans)")
            basis = _basis_line(growth)
            if basis:
                lines.append(basis)
        for p, price, value in rows:
            pnl = value - p.cost
            ret = pnl / p.cost if p.cost else 0.0
            lines.append(
                f"  {p.symbol.removesuffix('.IS')}: {tr(p.quantity)} adet × {tr(price, 2)} = {tr(value)} TL "
                f"(maliyet {tr(p.average_cost, 2)}; {'+' if pnl >= 0 else '-'}{tr(abs(pnl))} TL / {pct(ret)})"
            )
            support = guarded(lambda p=p: _support_line(p.symbol), "")
            if support:
                lines.append(support)
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
            budget_line, budget_alerts = _risk_budget(
                account, {p.symbol: value for p, _, value in rows},
                {p.symbol: adjusted_bars(p.symbol) for p, _, _ in rows}, total, bench["close"] if not bench.empty
                else pd.Series(dtype=float), growth if len(growth) >= 2 else None, day)
            if budget_line:
                lines.append(budget_line)
            alerts += budget_alerts
        alerts += evaluate_account(account, growth)

    events = guarded(lambda: update_alert_log(alerts, day, paths.alerts, write=record_alerts), [])
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
    for account in ACCOUNTS:  # holdings outside the universe are priced too: name them when old
        for p in open_positions(entries, account):
            raw = raw_bars(p.symbol)
            if p.symbol not in frames and p.symbol not in stale and (
                raw.empty or (pd.Timestamp(day) - raw.index[-1]).days > alert_cfg.STALE_DAYS
            ):
                stale.append(p.symbol)
    missing = [s for s in universe if s not in frames]
    if stale or missing or damaged or action_problems:
        lines += ["", "🔎 Veri notları"]
        lines += [f"  ⚠️ {text}" for text in damaged + action_problems]
        if missing:
            lines.append(f"  Verisi olmayan: {', '.join(s.removesuffix('.IS') for s in missing)}")
        if stale:
            lines.append(f"  Güncel olmayan: {', '.join(s.removesuffix('.IS') for s in stale)}")

    lines += ["", DISCLAIMER]
    return DailyResult(day, "\n".join(lines), events, fills)


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------


def _units(text: str) -> int:
    """Length as Telegram counts it: UTF-16 code units (an emoji outside the BMP is 2)."""

    return len(text.encode("utf-16-le")) // 2


def _cut(line: str, limit: int) -> tuple[str, str]:
    """The longest head of `line` within `limit` units, never splitting a character."""

    end = min(len(line), limit)
    while _units(line[:end]) > limit:
        end -= 1
    return line[:end], line[end:]


def split_text(text: str, limit: int = 4000) -> list[str]:
    """Parts of at most `limit` UTF-16 units, cut at line ends; a longer line is cut inside.
    The bot's replies use the same function (bot/common.py)."""

    parts, current = [], ""
    for line in text.splitlines(keepends=True):
        while _units(line) > limit:
            if current:
                parts.append(current)
                current = ""
            head, line = _cut(line, limit)
            parts.append(head)
        if _units(current) + _units(line) > limit and current:
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
        _restore_result(True, f"{len(checked)} dosya")
        return f"🔁 Haftalık geri yükleme testi başarılı: {len(checked)} dosya okundu (fiyat veritabanı dahil)"
    except Exception as exc:  # noqa: BLE001 - the report must still go out
        logger.exception("Weekly backup check failed")
        _restore_result(False, str(exc))
        return f"⚠️ Haftalık yedek/geri yükleme testi başarısız: {exc}"


def _restore_result(ok: bool, detail: str) -> None:
    from core.reports.slo import record_restore_test

    try:
        record_restore_test(ok, detail)
    except OSError:
        logger.exception("Restore test result not recorded")


def _alarm_hits(day: date) -> tuple[list, str | None]:
    """Price alarms crossed by `day`'s as-traded close: (hits, report line). Nothing is written
    here; _mark_alarms does that after the report went out. Never fatal."""

    from core.alerts import levels

    try:
        closes = {}
        for alarm in levels.active():
            bars = raw_bars(alarm.symbol)
            at = pd.Timestamp(day)
            if at in bars.index:
                closes[alarm.symbol] = float(bars.loc[at, "close"])
        hits = levels.check(day, closes, write=False)
        return hits, levels.format_hits(hits) or None
    except Exception as exc:  # noqa: BLE001 - the report must still go out
        logger.exception("Price alarms could not be checked")
        return [], f"⚠️ Fiyat alarmları kontrol edilemedi: {exc}"


def _support_line(symbol: str) -> str:
    from core.analytics.levels import position_line

    return position_line(adjusted_bars(symbol))


def _record_levels(day: date) -> None:
    """The day's cluster levels for today's BIST 100, after the report (Özellik A §3.4). Never fatal."""

    from core.analytics.levels import write_log

    try:
        symbols = _bist100_members() or load_universe()
        written = write_log(day, {s: adjusted_bars(s) for s in symbols})
        logger.info("Levels recorded | %d rows", written)
    except Exception:  # noqa: BLE001 - the report went out already
        logger.exception("Levels could not be recorded")


def _record_scenarios(day: date) -> None:
    """Özellik B §4.2: today's triggered scenarios of the BIST 100 into logs/scenarios_log.csv."""

    try:
        from core.analytics import scenarios
        from core.screen import universe
        from core.screen.command import _live

        frames, _bench = _live(universe.symbols("bist100"))
        logger.info("Scenarios recorded | %d", scenarios.write_log(day, frames))
    except Exception:  # noqa: BLE001 - the report was already sent
        logger.exception("Scenario recording failed")


def _refresh_scenario_cards(day: date) -> None:
    """On Fridays (or with no cache yet) the templates' card is recomputed for /senaryo."""

    try:
        from core.analytics import scenarios_study as study

        if day.weekday() != FRIDAY and study.CARDS_FILE.exists():
            return
        from core.screen import command

        study.save(study.study(command._history_data()))
    except Exception:  # noqa: BLE001 - the report was already sent
        logger.exception("Scenario card refresh failed")


def _screen_subscriptions(day: date, send) -> None:
    """/tara subscriptions after the report went out: only the changes, each its own message.
    The state is kept once they went out. Never fatal (DECISIONS K-42)."""

    from core.screen import subscriptions

    try:
        outcome = subscriptions.run(day)
        for message in outcome.messages:
            send(message)
        subscriptions.save_state(outcome)
    except Exception:  # noqa: BLE001 - the report went out already
        logger.exception("Screen subscriptions failed")
    return None


def _mark_alarms(hits: list) -> None:
    from core.alerts import levels

    try:
        levels.mark(hits)
    except Exception:  # noqa: BLE001 - announced already; worst case it is announced again tomorrow
        logger.exception("Price alarms could not be marked as triggered")


def _before_disclaimer(text: str, line: str) -> str:
    head, sep, tail = text.rpartition(DISCLAIMER)
    return f"{head}{line}\n\n{sep}{tail}" if sep else f"{text}\n\n{line}"


FRIDAY = 4


def _with_weekly_line(text: str, day: date) -> str:
    """On Fridays add the live-measurement and system summaries; never fatal."""

    if day.weekday() != FRIDAY:
        return text

    from core.reports import health
    from core.reports.forward import weekly_line

    try:
        text = _before_disclaimer(text, weekly_line())
    except Exception:  # noqa: BLE001 - the report must still go out
        logger.exception("Weekly summary failed")
    try:  # how the week went: reports sent, open problems, backup, monitoring
        text = _before_disclaimer(text, health.weekly_summary(day, health.health_checks(online=False)))
    except Exception:  # noqa: BLE001 - the report must still go out
        logger.exception("Weekly system summary failed")
    try:  # the service level objectives of docs/CHARTER.md §2, last 7 days
        from core.reports import slo

        text = _before_disclaimer(text, "\n".join(slo.lines(slo.measure(now_istanbul()))))
    except Exception:  # noqa: BLE001 - the report must still go out
        logger.exception("Weekly SLO table failed")
    try:  # DECISIONS K-23: the last day of the measurement window carries the server decision
        from core.reports import server_decision

        if server_decision.due(day):
            decision = server_decision.decide(now=now_istanbul())
            text = _before_disclaimer(text, server_decision.format_decision(decision))
    except Exception:  # noqa: BLE001 - the report must still go out
        logger.exception("Server decision failed")
    return text


def _record_scores() -> str:
    """Record every stock's view for the live measurement; never fatal. Returns a warning line or ""."""

    from core.reports.forward import log_daily_scores, log_elimination_groups

    try:
        written = log_daily_scores(load_universe())
        logger.info("Daily scores recorded | %d stocks", written)
    except Exception as exc:  # noqa: BLE001 - the report must still go out, and say what is missing
        logger.exception("Daily score recording failed")
        return f"⚠️ Canlı ölçüm kaydı yazılamadı ({type(exc).__name__}: {exc}); bu gün ölçümden eksik kalır"
    try:
        logger.info("Elimination groups recorded | %d stocks", log_elimination_groups(_elimination_result()))
    except Exception as exc:  # noqa: BLE001 - one extra measurement never stops the report
        logger.exception("Elimination recording failed")
        return f"⚠️ Eleme ölçümü kaydı yazılamadı ({type(exc).__name__}: {exc}); bu gün eksik kalır"
    return ""


def _elimination_result():
    """Today's BIST 100 through the default /tara elimination (K-45), with a condition every stock meets."""

    from core.screen import engine, universe
    from core.screen.command import _live
    from core.screen.language import parse

    frames, bench = _live(universe.symbols("bist100"))
    return engine.run(parse("kapanis>0"), frames, bench, universe.suspects())


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


# After sleep the scheduled task starts as soon as the PC wakes, often before Wi-Fi is back.
# When not a single symbol downloads, wait and try again (1 + 2 + 4 minutes) before giving up.
NETWORK_WAITS = (60, 120, 240)


def update_prices(symbols: list[str], update=None, sleep=None) -> dict[str, str]:
    import time

    update = update or store.update
    sleep = sleep or time.sleep
    status = update(symbols)
    for pause in NETWORK_WAITS:
        if not status or any(v != "failed" for v in status.values()):
            break
        logger.warning("No price could be downloaded (network?); trying again in %d s", pause)
        sleep(pause)
        status = update(symbols)
    return status


def _record_freshness(universe: list[str] | None = None, now=None) -> None:
    """How many universe stocks (and XU100) have the expected session's close: the 'veri tazeliği' objective."""

    from core.reports.slo import record_freshness

    try:
        now = now or now_istanbul()
        expected = last_final_session_date(now)
        universe = universe or load_universe()
        have = sum(store.last_date(s) == expected for s in universe)
        record_freshness(expected, have, len(universe), store.last_date(BENCHMARK) == expected, now=now)
    except Exception:  # noqa: BLE001 - measuring must never stop the report
        logger.exception("Freshness not recorded")


REPORT_TEXT_DIR = LOG_DIR / "reports"  # SPOF T-1: the day's report survives a Telegram outage


def _keep_report_text(day, text: str, prefix: str = "rapor_") -> Path | None:
    """Save what is about to be sent (one file per data day; a resend replaces it). Never fatal."""

    try:
        REPORT_TEXT_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORT_TEXT_DIR / f"{prefix}{day if isinstance(day, str) else day.isoformat()}.txt"
        path.write_text(text, encoding="utf-8")
        return path
    except OSError:
        logger.exception("Report text not saved")
        return None


def _parse_day(text: str, today: date) -> date | None:
    """27.10, 27.10.2026 or 2026-10-27; a day-month without a year is the latest one not in the future."""

    from datetime import datetime

    text = text.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    try:
        day = datetime.strptime(f"{text}.{today.year}", "%d.%m.%Y").date()
    except ValueError:
        return None
    return day if day <= today else day.replace(year=today.year - 1)


def saved_report(day_text: str | None) -> str:
    """/rapor_tekrar: the newest saved report, or the one of a given data day (SPOF T-1 files)."""

    folder = REPORT_TEXT_DIR
    files = sorted(folder.glob("rapor_????-??-??.txt")) if folder.exists() else []
    if not day_text:
        if not files:
            return "Kayıtlı rapor yok: v0.57.0'dan beri gönderilen her rapor logs/reports/ klasörüne yazılır."
        return files[-1].read_text(encoding="utf-8")
    day = _parse_day(day_text, now_istanbul().date())
    if day is None:
        return "Tarih anlaşılmadı. Örnek: /rapor_tekrar 27.10 ya da /rapor_tekrar 27.10.2026"
    path = folder / f"rapor_{day.isoformat()}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    known = ", ".join(f"{date.fromisoformat(f.stem[-10:]):%d.%m.%Y}" for f in files[-5:]) or "hiç yok"
    return f"{day:%d.%m} için kayıtlı rapor yok. Kayıtlı son raporlar: {known}"


def _held_symbols(paths: Paths | None = None) -> list[str]:
    entries = load_ledger((paths or Paths()).ledger)
    return sorted({p.symbol for account in ACCOUNTS for p in open_positions(entries, account)})


def _second_source_note(expected: date, symbols: list[str], fetch=None) -> str | None:
    """SPOF Y-1: the expected session's closes from İş Yatırım, for information only. None when it has none.

    Never written to the price store: it has no open, and paper fills and the live measurement
    use the open. They wait for Yahoo; the store catches up by itself when Yahoo is back.
    """

    from core.market.crosscheck import fetch_isyatirim

    fetch = fetch or (lambda *a, **k: fetch_isyatirim(*a, retries=1, **k))  # information only: one try
    closes, index = [], None
    for symbol in symbols or ["THYAO.IS"]:  # every İş Yatırım row also carries BIST 100
        try:
            frame = fetch(symbol.removesuffix(".IS"), expected - timedelta(days=7), expected)
        except Exception:  # noqa: BLE001 - a second source that is down just means no message
            logger.warning("Second source unavailable | %s", symbol, exc_info=True)
            return None
        stamp = pd.Timestamp(expected)
        if frame.empty or stamp not in frame.index:
            continue
        row = frame.loc[stamp]
        if symbols:
            closes.append(f"  {symbol.removesuffix('.IS')} {tr(float(row['close']), 2)}")
        if index is None and pd.notna(row.get("index")):
            index = float(row["index"])
    if index is None and not closes:
        return None
    lines = [f"⚠️ Yahoo'dan {expected:%d.%m.%Y} kapanışı alınamadı; tam rapor veri gelince ilk çalışmada.",
             "İkinci kaynak (İş Yatırım), yalnız bilgi:"]
    if index is not None:
        lines.append(f"  XU100 {tr(index)}")
    lines += closes
    lines += ["Sanal emirler, hesap değeri ve canlı ölçüm Yahoo verisi gelince işlenir.", "", DISCLAIMER]
    return "\n".join(lines)


def _send_second_source(args) -> str:
    """Once per missing session: a marker in REPORT_TEXT_DIR is written only after it went out."""

    from core.infrastructure.settings import require_bot_settings

    expected = last_final_session_date(now_istanbul())
    marker = REPORT_TEXT_DIR / f"ikinci_kaynak_{expected.isoformat()}.txt"
    if marker.exists():
        return ""
    try:
        text = _second_source_note(expected, _held_symbols())
        if not text:
            return ""
        s = require_bot_settings()
        send_telegram(text, s.bot_token, s.chat_id)
        _keep_report_text(f"ikinci_kaynak_{expected.isoformat()}", text, prefix="")
        return "ikinci kaynak bilgisi gönderildi"
    except Exception:  # noqa: BLE001 - a stale day stays a stale day, never an error
        logger.exception("Second-source message not sent")
        return ""


def _risk_budget(account, values, frames, total, bench, perf, day, limits=None) -> tuple[str, list]:
    """Talimat E: one line and the limit alerts; never fatal (K-56)."""

    try:
        from core.alerts import budget

        problems: list[str] = []
        limits = budget.load_limits(account, problems=problems) if limits is None else limits
        table = budget.rows(budget.measure(values, frames, total, bench, perf), limits)
        line = budget.summary_line(table)
        if problems:  # validation M28: a mistyped limit is never silently off
            line += f"; ⚠️ risk_limits.csv'de {len(problems)} satır sorunlu (/risk)"
        return line, budget.evaluate_limits(account, table, day)
    except Exception:  # noqa: BLE001 - extra information; the report still goes out
        logger.exception("Risk budget failed")
        return "", []


def _basis_line(growth: pd.Series) -> str:
    """Talimat C: growth since the first record, nominal / real / USD / against cash (K-51)."""

    try:
        from core.market import macro

        start, end = growth.index[0].date(), growth.index[-1].date()
        result = macro.four_basis(float(growth.iloc[-1] / growth.iloc[0] - 1), start, end)
        return f"{start:%d.%m.%Y}'den bu yana: {result.line()}"
    except Exception:  # noqa: BLE001 - extra information; the report still goes out
        logger.exception("Four-basis line failed")
        return ""


def _update_macro() -> None:
    """Talimat C: the last two weeks of TCMB bulletins not yet cached (at most 10 requests, 30 s)
    and, after the 3rd of a month, the new CPI figure from TCMB's table (one request)."""

    try:
        from core.market import macro

        today = date.today()
        macro.update_usdtry(today - timedelta(days=14), today, limit=10, budget=30)
        macro.update_cpi(today)
        macro.save_second_source(macro.second_source_check(macro.load_usdtry(), today))
    except Exception:  # noqa: BLE001 - the report never waits on this
        logger.exception("Macro data update failed")


def _run(args) -> DailyResult:
    with report_lock():
        return _run_locked(args)


def _run_locked(args) -> DailyResult:
    yahoo_down = False  # Yahoo did not answer for XU100 (not merely late with today's candle)
    if not args.no_update:
        status = update_prices(symbols_to_update())
        yahoo_down = status.get(BENCHMARK) in ("failed", "empty")
        failed = [s for s, v in status.items() if v in ("failed", "empty")]
        if failed:
            logger.warning("Daily update: no data for %s", ", ".join(failed))
        _record_freshness()
        _update_macro()

    result = build_daily()
    score_warning = _record_scores()

    if args.send and not args.force and already_sent(result.day):
        # never send the same data day twice; say why in logs/runs.csv
        result.status, result.note = _not_sent_reason(result.day)
        if result.status == "stale" and yahoo_down:  # a late candle comes later; no second source for that
            sent = _send_second_source(args)
            if sent:
                result.note = f"{result.note}; {sent}"
        logger.info("Daily report for %s was already sent (%s); not sending again", result.day, result.status)
        return result

    result.text = _with_weekly_line(result.text, result.day)
    hits, alarm_line = _alarm_hits(result.day)
    if alarm_line:
        result.text = _before_disclaimer(result.text, alarm_line)
    if score_warning:
        result.text = _before_disclaimer(result.text, score_warning)
    result.text = _with_backup_line(result.text)
    result.text = _with_health_warnings(result.text)

    # send first: a problem while printing must never stop the report
    if args.send:
        from core.infrastructure.settings import require_bot_settings

        s = require_bot_settings()
        _keep_report_text(result.day, result.text)
        send_telegram(result.text, s.bot_token, s.chat_id)
        result.status = "sent"
        _mark_alarms(hits)
        logger.info("Daily report sent to Telegram | %s", result.day)
        _screen_subscriptions(result.day, lambda text: send_telegram(text, s.bot_token, s.chat_id))
        _record_levels(result.day)
        _record_scenarios(result.day)
        _refresh_scenario_cards(result.day)
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
        log_file = Path(args.log_dir) / f"daily_{started:%Y-%m-%d}.log"  # Istanbul date

    def write_log(text: str) -> None:
        if log_file is not None:
            with open(log_file, "a", encoding="utf-8") as fh:
                fh.write(f"\n===== {now_istanbul():%Y-%m-%d %H:%M:%S} =====\n{text}\n")

    run_id = f"{started:%Y%m%d-%H%M%S}-{os.getpid()}"

    def run_line(status: str, day=None, detail: str = "") -> None:
        """One searchable line per run: 'RUN daily' finds every run, 'status=failed' the errors."""

        seconds = int((now_istanbul() - started).total_seconds())
        line = (f"RUN daily id={run_id} status={status} day={day.isoformat() if day else '-'} "
                f"duration={seconds}s" + (f" detail={detail.replace(chr(10), ' ')[:200]}" if detail else ""))
        (logger.error if status == "failed" else logger.info)("%s", line)
        if log_file is not None:
            with open(log_file, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    try:
        result = _run(args)
    except ReportBusy as exc:
        # another run is doing the work right now; not a failure
        logger.warning("%s", exc)
        write_log(f"ATLANDI: {exc}")
        record_run(started, "busy", detail=str(exc))
        run_line("busy", detail=str(exc))
        print(exc)
        return 0
    except Exception as exc:  # noqa: BLE001 - the scheduled run must leave a trace
        error = traceback.format_exc()
        logger.error("Daily report failed\n%s", error)
        write_log("HATA\n" + error)
        record_run(started, "failed", detail=f"{type(exc).__name__}: {exc}")
        run_line("failed", detail=f"{type(exc).__name__}: {exc}")
        print(error, file=sys.stderr)
        if args.send:
            _notify_failure(exc, str(log_file or "logs/quantbist.log"))
            ping.ping(ping.address(ping.REPORT_ENV), fail=True, name=ping.REPORT_ENV)
        return 1

    record_run(started, result.status, result.day, result.note)
    if args.send:  # outside monitoring: a holiday or an already sent day is fine; no new data is not
        ping.ping(ping.address(ping.REPORT_ENV), fail=result.status not in ("sent", "skipped", "holiday"),
                  name=ping.REPORT_ENV)
    note = "\n\nTelegram'a gönderildi." if result.status == "sent" else (
        f"\n\nTelegram'a gönderilmedi ({result.status}: {result.note})." if result.note else ""
    )
    write_log(result.text + note)
    run_line(result.status, result.day, result.note)
    print(result.text + note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Paths", "DailyResult", "build_daily", "send_telegram", "split_text", "main"]
