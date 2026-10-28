"""
QuantBIST
The /tara engine: which stocks meet a query on the latest closed session.

- Stocks whose last close is not the latest session are left out and NAMED in the answer;
  nothing is dropped silently.
- The elimination filters (core.screen.elimination: liquidity, corporate action, extreme move,
  data problem incl. a second-source difference) are applied after the rank fields are computed,
  so gg_sira ranks the whole scanned list; each eliminated stock is named with its reason.
- Only closed candles are used; during a session the answer says which close it is based on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from core.screen import fields as F
from core.screen import language as L
from core.screen.language import Query

LOOKBACK = 62  # son(60, ...) plus the cross's previous session
DISPLAY = ("kapanis", "atr", "islem_tl", "gg_20", "hacim_oran", "rsi")
ORDER_KEYS = {"goreli_guc": ("gg_20", True), "hacim": ("hacim_oran", True), "rsi": ("rsi", False)}


LABELS = {"rsi": "RSI", "ema20": "EMA20", "ema50": "EMA50", "ema200": "EMA200", "macd": "MACD",
          "macd_sinyal": "MACD sinyal", "macd_hist": "MACD hist", "hacim_oran": "hacim", "kapanis": "kapanış",
          "adx": "ADX", "atr": "ATR", "islem_tl": "işlem"}


def label(column: str) -> str:
    return LABELS.get(column, column.upper() if column.startswith(("ema(", "sma(", "rsi(")) else column)


def value_text(column: str, x: float) -> str:
    from core.reports.daily import tr

    if x != x:
        return "—"
    unit = F.FIELDS[F.split(column)[0]].unit
    if unit == "×":
        return f"{tr(x, 1)}×"
    if unit == "milyon TL":
        return f"{tr(x, 0)} mn TL"
    if unit == "adet":
        return tr(x, 0)
    if unit in ("%", "puan", "0–100", "±1"):
        return tr(x, 1)
    return tr(x, 2) if abs(x) < 1000 else tr(x, 0)


def describe(node, tail: pd.DataFrame) -> list[str]:
    """The parts of the query that hold on the last row, with their values."""

    if not bool(node.mask(tail).iloc[-1]):
        return []
    row = tail.iloc[-1]
    if isinstance(node, (L.And, L.Or)):
        return [part for c in node.children for part in describe(c, tail)]
    if isinstance(node, L.Not):
        return [f"değil {node.child.text(True)}"]
    if isinstance(node, L.Within):
        return [f"son {node.days} gün içinde {node.child.text(False)}"]
    if isinstance(node, L.Cross):
        return [f"{label(node.a.text)} {'↗' if node.up else '↘'} {label(node.b.text)} (kesişim bugün)"]
    if isinstance(node, L.Range):
        return [f"{label(node.operand.key)} {value_text(node.operand.key, row[node.operand.key])}"]
    left, right = node.left, node.right
    if left.key is not None and right.key is not None:
        return [f"{label(left.key)}{node.op}{label(right.key)}"]
    column = left.key if left.key is not None else right.key
    return [f"{label(column)} {value_text(column, row[column])}"]


@dataclass
class Match:
    symbol: str
    day: date
    values: dict
    met: list = field(default_factory=list)
    flags: list = field(default_factory=list)

    @property
    def close(self) -> float:
        return self.values["kapanis"]

    @property
    def atr(self) -> float:
        return self.values["atr"]

    @property
    def liquidity(self) -> float:
        return self.values["islem_tl"]


@dataclass
class Result:
    query: Query
    day: date | None
    matches: list[Match] = field(default_factory=list)
    missing: list[tuple[str, str]] = field(default_factory=list)  # (symbol, why)
    eliminated: list[tuple[str, str]] = field(default_factory=list)  # (symbol, reasons)
    scanned: int = 0
    funnel: list = field(default_factory=list)  # (condition, alone, cumulative) when nothing matched

    @property
    def illiquid(self) -> list[str]:
        return [s for s, why in self.eliminated if why.startswith("likidite")]


def columns(query: Query) -> list[str]:
    return list(dict.fromkeys([*sorted(query.fields), *DISPLAY]))


def run(query: Query, frames: dict[str, pd.DataFrame], bench: pd.DataFrame,
        suspects: set[str] | None = None, actions=None) -> Result:
    from core.screen import elimination as E

    latest = bench.index[-1]
    result = Result(query, latest.date())
    suspects = suspects or set()
    actions = E.corporate_actions() if actions is None else actions
    tables: dict[str, pd.DataFrame] = {}
    checks: dict[str, pd.Series] = {}
    wanted = columns(query)
    for symbol in sorted(frames):
        df = frames[symbol]
        if df is None or df.empty:
            result.missing.append((symbol, "fiyat verisi yok"))
        elif df.index[-1] != latest:
            result.missing.append((symbol, f"son kapanış {df.index[-1]:%d.%m}"))
        else:
            tables[symbol] = F.table(df, bench["close"], wanted)
            checks[symbol] = E.frame(df, symbol, bench.index, actions).iloc[-1]
    result.scanned = len(tables)
    cut = E.atr_cut([c["atr_pct"] for c in checks.values()]) if query.elimination.move else None

    if "gg_sira" in query.fields and tables:
        last = pd.Series({s: t["gg_60"].iloc[-1] for s, t in tables.items()})
        ranks = last.rank(pct=True) * 100
        for s, t in tables.items():
            t.loc[t.index[-1], "gg_sira"] = ranks.get(s)

    for symbol, t in tables.items():
        row = t.iloc[-1]
        why = E.reasons(checks[symbol], query.elimination, cut, symbol.removesuffix(".IS") in suspects)
        if why:
            result.eliminated.append((symbol, ", ".join(why)))
            continue
        tail = t.iloc[-LOOKBACK:]  # fields use the full history; the logic looks back ≤ 61 sessions
        if bool(query.mask(tail).iloc[-1]):
            result.matches.append(Match(symbol, latest.date(), {c: float(row[c]) for c in t.columns},
                                        describe(query.root, tail), flags(frames[symbol])))

    if not result.matches:
        out = {s for s, _ in result.eliminated}
        result.funnel = funnel(query, {s: t for s, t in tables.items() if s not in out})

    if query.order in ORDER_KEYS:
        column, descending = ORDER_KEYS[query.order]

        def sort_key(m: Match):
            value = m.values.get(column, float("nan"))
            missing = value != value
            return (missing, -value if descending and not missing else value if not missing else 0.0, m.symbol)

        result.matches.sort(key=sort_key)
    return result


SHARP_MOVE = 0.30  # a limit-down or limit-up streak: ATR built at another price level (ANELE, 19-27.10.2026)
LIMIT_MOVE = 0.105  # BIST's daily price limit is ±10%; a bigger close-to-close move is data or an action


def flags(df: pd.DataFrame) -> list[str]:
    """Warnings for a matched row: an ATR built on a move no session allows (ANELE, 27.10.2026)."""

    from core.reports.daily import pct

    close = df["close"]
    found = []
    moves = (close / close.shift(1) - 1).iloc[-14:].abs()
    if (moves > LIMIT_MOVE).any():
        found.append("ATR son 14 seansta ±%10 limitini aşan bir hareket içeriyor (uç hareket: veri ya da kurumsal "
                     "işlem; /tara_aciklama ile bakın)")
    if len(close) > 14:
        change = close.iloc[-1] / close.iloc[-15] - 1
        if abs(change) > SHARP_MOVE:
            found.append(f"son 14 seansta fiyat {pct(change)} değişti: ATR bu sert hareketle şişmiş olabilir "
                         "(aralıklar farklı fiyat düzeyinde oluştu)")
    return found


def funnel(query: Query, tables: dict) -> list[tuple[str, int, int]]:
    """For each top-level condition: how many scanned stocks meet it alone, and how many are left
    after it and every condition before it (the cumulative count is only meaningful for 've')."""

    parts = list(query.root.children) if isinstance(query.root, L.And) else [query.root]
    tails = [t.iloc[-LOOKBACK:] for t in tables.values()]
    out, alive = [], [True] * len(tails)
    for part in parts:
        holds = [bool(part.mask(t).iloc[-1]) for t in tails]
        alive = [a and h for a, h in zip(alive, holds, strict=True)]
        out.append((part.text(False), sum(holds), sum(alive)))
    return out


def time_note(day: date, now: datetime) -> str:
    """'27.10.2026 kapanışına göre (bugünün seansı henüz kapanmadı)' when run during a session."""

    from core.market.calendar import is_session_day, last_final_session_date

    if now.date() <= day:
        return ""
    note = f"{day:%d.%m.%Y} kapanışına göre"
    if is_session_day(now.date()) and last_final_session_date(now) < now.date():
        note += " (bugünün seansı henüz kapanmadı)"
    return note


__all__ = ["DISPLAY", "Match", "Result", "columns", "describe", "label", "run", "time_note", "value_text"]
