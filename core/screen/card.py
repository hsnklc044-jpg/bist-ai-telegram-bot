"""
QuantBIST
The /tara history card, honest by construction (DECISIONS K-35).

- Period 2023-08-01 – 30.10.2026 (the research period). The holdout (from 02.11.2026) is never
  read: the data comes through load_frames, and the card cuts it again here.
- Each day the query held for a stock that was a BIST 100 member that day (no survivorship):
  enter at the NEXT session's open (no look-ahead), exit at the close `h` sessions later, pay
  the research costs both ways (commission 0.10% + slippage 0.05%), minus XU100 over the same
  sessions.
- Shown: mean and median excess, hit rate, samples, independent events (a stock's signals inside
  one holding period count once), a block-bootstrap 95% interval (circular blocks of BLOCK = 20 entry
  dates; the signals of a date move together), and the mean without the 5 most profitable stocks.
- Labels never call the past evidence: queries can be tried freely (no research budget, no
  pre-registration), so even a positive interval may be luck. The criteria tried are counted.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from core.config.paths import DATA_DIR, LOG_DIR
from core.market.limits import locked_up
from core.screen import fields as F
from core.screen.language import Query

HISTORY_START = "2023-08-01"
HORIZONS = (5, 20)
MIN_SAMPLES = 30
ROUND_TRIP_COST = 2 * (0.0010 + 0.0005)  # the research costs (RESEARCH_LOG), both ways
BLOCK = 20  # sessions per bootstrap block (görev 28.10, Aşama C)
SAMPLES = 2000
TOP_EXCLUDED = 5
CACHE_FILE = LOG_DIR / "screen_cards.json"
CARD_FORMAT = 5  # 5: Faz C M5 (delisted exits, longer blocks, independent dates, membership end); 4: elimination filters day by day (K-45); 3: jumped stocks left out (öz-denetim 6, D1); bumped when the card's statistics change: older cached cards are recomputed
CACHE_LIMIT = 500  # cards kept on disk, newest last (öz-denetim 5, Ö18)
TRIALS_FILE = LOG_DIR / "screen_trials.csv"
VERSION_FILES = (DATA_DIR / "corporate_actions.csv", DATA_DIR / "price_fix_approvals.csv",
                 DATA_DIR / "bist100_changes.csv", DATA_DIR / "bist100_stable.csv")


@dataclass
class CardStats:
    n: int = 0
    independent: int = 0
    mean: float | None = None
    median: float | None = None
    hit: float | None = None
    low: float | None = None
    high: float | None = None
    without_top: float | None = None
    gross: float | None = None  # event mean before costs
    day_mean: float | None = None  # mean of the daily means (each entry date once); low/high are its interval
    base: float | None = None  # the same day mean for every eligible stock-day ("tüm hisseler")
    no_index: bool = False  # XU100 was missing: nothing could be measured
    independent_dates: int = 0  # Faz C M5-8: entry dates at least h sessions apart, all stocks together

    @property
    def label(self) -> str:
        if self.no_index:
            return "XU100 verisi yok; karne hesaplanamadı"
        if self.n < MIN_SAMPLES or self.low is None:
            return "yetersiz örnek"
        if self.low > 0:
            # M5 ORTA: ahead of XU100 is not enough; the screen must also beat "tüm hisseler" (the same
            # days without the screen), else it selected nothing (kapanis>0 was "olumlu")
            if self.base is not None and not self.low > self.base:
                return "geçmişte XU100'ün önünde ama tüm hisselerden ayırt edilemiyor; tarama bir şey seçmedi"
            return "geçmişte olumlu; çoklu deneme nedeniyle şans olabilir, kanıt değildir"
        if self.high < 0:
            return "geçmişte XU100'ün gerisinde; kanıt değildir"
        return "geçmişte XU100'den ayırt edilemiyor"


def _tables(query: Query, frames: dict, bench: pd.DataFrame, eligible: pd.DataFrame | None) -> dict:
    wanted = sorted(query.fields | {"islem_tl"})
    tables = {s: F.table(df, bench["close"], wanted) for s, df in frames.items() if not df.empty}
    if tables:
        F.rank_panel(tables, sorted(query.fields & F.CROSS_SECTIONAL), eligible)
    return tables


def _independent(positions: np.ndarray, horizon: int) -> int:
    count, last = 0, None
    for p in positions:
        if last is None or p - last >= horizon:
            count, last = count + 1, p
    return count


def _day_means(dates: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Mean excess of each entry date, in date order."""

    order = np.argsort(dates, kind="stable")
    dates, values = dates[order], values[order]
    _, start = np.unique(dates, return_index=True)
    return np.add.reduceat(values, start) / np.diff(np.append(start, len(values)))


def block_for(horizon: int) -> int:
    """Faz C M5-7: a block of only `horizon` sessions covered ~90% at h = 20; at least twice the holding."""

    return max(BLOCK, 2 * horizon)


def _interval(days: np.ndarray, seed: int = 0, block: int = BLOCK) -> tuple[float, float] | tuple[None, None]:
    """95% circular block bootstrap of the mean of the daily means (blocks of `block` sessions)."""

    n = len(days)
    if n < 2 * block:
        return None, None
    rng = np.random.default_rng(seed)
    blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(SAMPLES, blocks))
    index = ((starts[:, :, None] + np.arange(block)) % n).reshape(SAMPLES, -1)[:, :n]
    low, high = np.quantile(days[index].mean(axis=1), [0.025, 0.975])
    return float(low), float(high)


def history(query: Query, frames: dict[str, pd.DataFrame], bench: pd.DataFrame,
            eligible: pd.DataFrame | None = None, horizons=HORIZONS, actions=None) -> dict[int, CardStats]:
    from core.backtest.run import SCREEN_END
    from core.screen import elimination as E

    if bench is None or bench.empty:  # M5-6: no index, no excess return: said, not "yetersiz örnek"
        return {h: CardStats(no_index=True) for h in horizons}
    bench = bench.loc[:SCREEN_END]
    frames = {s: df.loc[:SCREEN_END] for s, df in frames.items()}
    tables = _tables(query, frames, bench, eligible)
    actions = E.corporate_actions() if actions is None else actions
    members: dict[str, np.ndarray] = {}
    checks: dict[str, pd.DataFrame] = {}
    for symbol, table in tables.items():
        ok = table.index >= pd.Timestamp(HISTORY_START)
        if eligible is not None:
            if symbol not in eligible.columns:
                continue
            member = eligible[symbol]
            held = member.reindex(table.index).ffill().fillna(False).astype(bool).to_numpy()
            ok &= held & (table.index <= member.index.max())  # Faz C M5-9: not carried past the table
        members[symbol] = ok
        checks[symbol] = E.frame(frames[symbol], symbol, bench.index, actions)
    # the same eliminations as the live list, each day with its own data (K-45)
    cut = E.daily_cut(checks, members) if query.elimination.move and checks else None
    chosen = None
    if query.regime:  # only the days whose own regime label is the chosen one (K-51)
        from core.market import regime
        from core.screen.language import REGIMES

        chosen = regime.labels(bench["close"], frames, eligible) == REGIMES[query.regime]
    rows: dict[int, list] = {h: [] for h in horizons}
    base: dict[int, list] = {h: [] for h in horizons}
    independent = dict.fromkeys(horizons, 0)
    for symbol, ok in members.items():
        table, df = tables[symbol], frames[symbol]
        universe = ok & ~E.mask(checks[symbol], query.elimination, cut)
        if chosen is not None:
            universe &= chosen.reindex(table.index).fillna(False).astype(bool).to_numpy()
        if not universe.any():
            continue
        mask = query.mask(table).to_numpy() & universe
        b = bench.reindex(df.index)
        entry, bench_entry = df["open"].shift(-1), b["open"].shift(-1)
        # K-75 (M5-3): an entry day locked at the upper limit does not fill
        entry = entry.where(~pd.Series(locked_up(df), index=df.index).shift(-1, fill_value=False))
        # Faz C M5-5: a stock whose data ends before the period (delisted) exits at its last close; its last
        # events used to vanish (a −40% fall was not counted)
        ended = len(df) and df.index[-1] < bench.index[-1]
        for h in horizons:
            exit_, bench_exit = df["close"].shift(-h), b["close"].shift(-h)
            if ended:
                tail = exit_.isna() & entry.notna()
                exit_, bench_exit = exit_.where(~tail, df["close"].iloc[-1]), bench_exit.where(~tail, b["close"].iloc[-1])
            gross = ((exit_ / entry - 1) - (bench_exit / bench_entry - 1)).to_numpy()
            excess = gross - ROUND_TRIP_COST
            # a zero or missing open makes ±inf, not NaN (M5 ORTA): only finite results count
            every = np.flatnonzero(universe & np.isfinite(excess))  # "tüm hisseler": the same days without the query
            base[h].append(pd.DataFrame({"date": df.index[every].to_numpy(), "excess": excess[every]}))
            positions = np.flatnonzero(mask & np.isfinite(excess))
            if len(positions):
                rows[h].append(pd.DataFrame({"symbol": symbol, "date": df.index[positions].to_numpy(),
                                             "excess": excess[positions], "gross": gross[positions]}))
                independent[h] += _independent(positions, h)
    out = {}
    for h in horizons:
        if not rows[h]:
            out[h] = CardStats()
            continue
        events = pd.concat(rows[h], ignore_index=True)
        values = events["excess"].to_numpy()
        days = _day_means(events["date"].to_numpy(), values)
        low, high = _interval(days, block=block_for(h))
        dates = np.unique(events["date"].to_numpy())
        independent_dates = _independent(np.sort(bench.index.get_indexer(dates)), h)
        best = events.groupby("symbol")["excess"].sum().nlargest(TOP_EXCLUDED).index
        rest = events.loc[~events["symbol"].isin(best), "excess"]
        everyone = pd.concat(base[h], ignore_index=True)
        base_days = _day_means(everyone["date"].to_numpy(), everyone["excess"].to_numpy())
        out[h] = CardStats(len(values), independent[h], float(values.mean()), float(np.median(values)),
                           float((values > 0).mean()), low, high, float(rest.mean()) if len(rest) else None,
                           float(events["gross"].mean()), float(days.mean()), float(base_days.mean()),
                           independent_dates=independent_dates)
    return out


# --- cache ----------------------------------------------------------------------------------------

_MEMORY: dict = {}


def data_version(files=VERSION_FILES) -> str:
    """Changes when a correction or the membership changes (the screening period is fixed)."""

    from core.backtest.run import SCREEN_END

    digest = hashlib.sha256(f"{SCREEN_END}|{CARD_FORMAT}".encode())
    for path in files:
        path = Path(path)
        digest.update(path.read_bytes() if path.exists() else b"-")
    return digest.hexdigest()[:12]


def peek(query: Query, version: str | None = None, path: Path | None = None) -> dict | None:
    """The cached card, or None: never computes (for lists that must not wait)."""

    path = Path(path or CACHE_FILE)
    key = f"{query.text}|{version or data_version()}"
    if key in _MEMORY:
        return _MEMORY[key]
    try:
        stored = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        return None
    if key not in stored:
        return None
    _MEMORY[key] = {int(h): CardStats(**v) for h, v in stored[key].items()}
    return _MEMORY[key]


def cached_history(query: Query, load, version: str | None = None, path: Path | None = None) -> dict:
    """The card for (criterion, data version): from memory, then from disk, else computed once."""

    path = Path(path or CACHE_FILE)
    key = f"{query.text}|{version or data_version()}"
    if key in _MEMORY:
        return _MEMORY[key]
    try:
        stored = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        stored = {}
    if key in stored:
        result = {int(h): CardStats(**v) for h, v in stored[key].items()}
    else:
        result = history(query, *load())
        stored[key] = {str(h): asdict(v) for h, v in result.items()}
        stored = dict(list(stored.items())[-CACHE_LIMIT:])
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp")  # one temp file per process (bot + report)
            tmp.write_text(json.dumps(stored, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
        except OSError:
            pass  # a cache that cannot be written only costs time
    _MEMORY[key] = result
    return result


# --- the criteria tried (data-snooping warning) ---------------------------------------------------

_SESSIONS: dict = {}  # chat -> criteria tried since the bot started


def record_trial(chat_id, criterion: str, path: Path | None = None, session: dict | None = None,
                 now: datetime | None = None) -> tuple[int, int]:
    """(this criterion's place in the session, distinct criteria tried in total)."""

    from core.infrastructure.csvfiles import open_append, read_rows
    from core.market.calendar import now_istanbul

    path = Path(path or TRIALS_FILE)
    session = _SESSIONS if session is None else session
    tried = session.setdefault(chat_id, [])
    if criterion not in tried:
        tried.append(criterion)
    known = {row["criterion"] for _, row in read_rows(path, ("at", "chat", "criterion"))} if path.exists() else set()
    if criterion not in known:
        fh, new_file = open_append(path)
        with fh:
            writer = csv.writer(fh, lineterminator="\n")
            if new_file:
                writer.writerow(("at", "chat", "criterion"))
            writer.writerow([(now or now_istanbul()).isoformat(timespec="seconds"), chat_id, criterion])
        known.add(criterion)
    return tried.index(criterion) + 1, len(known)


__all__ = ["CardStats", "HISTORY_START", "HORIZONS", "MIN_SAMPLES", "ROUND_TRIP_COST", "cached_history",
           "data_version", "history", "record_trial"]
