"""
QuantBIST
The /tara engine: which stocks meet a query on the latest closed session.

- Stocks whose last close is not the latest session, or whose prices wait for a correction
  (the second source differs: crosscheck/latest.json), are left out and NAMED in the answer;
  nothing is dropped silently.
- The liquidity floor (20-session mean turnover, million TL; default 10, likidite=0 turns it
  off) is applied after the rank fields are computed, so gg_sira ranks the whole scanned list.
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
    illiquid: list[str] = field(default_factory=list)
    scanned: int = 0


def columns(query: Query) -> list[str]:
    return list(dict.fromkeys([*sorted(query.fields), *DISPLAY]))


def run(query: Query, frames: dict[str, pd.DataFrame], bench: pd.DataFrame,
        suspects: set[str] | None = None) -> Result:
    latest = bench.index[-1]
    result = Result(query, latest.date())
    suspects = suspects or set()
    tables: dict[str, pd.DataFrame] = {}
    wanted = columns(query)
    for symbol in sorted(frames):
        df = frames[symbol]
        if df is None or df.empty:
            result.missing.append((symbol, "fiyat verisi yok"))
        elif df.index[-1] != latest:
            result.missing.append((symbol, f"son kapanış {df.index[-1]:%d.%m}"))
        elif symbol.removesuffix(".IS") in suspects:
            result.missing.append((symbol, "ikinci kaynakta fark (düzeltme bekliyor)"))
        else:
            tables[symbol] = F.table(df, bench["close"], wanted)
    result.scanned = len(tables)

    if "gg_sira" in query.fields and tables:
        last = pd.Series({s: t["gg_60"].iloc[-1] for s, t in tables.items()})
        ranks = last.rank(pct=True) * 100
        for s, t in tables.items():
            t.loc[t.index[-1], "gg_sira"] = ranks.get(s)

    for symbol, t in tables.items():
        row = t.iloc[-1]
        if query.liquidity > 0 and not (row["islem_tl"] >= query.liquidity):
            result.illiquid.append(symbol)
            continue
        tail = t.iloc[-LOOKBACK:]  # fields use the full history; the logic looks back ≤ 61 sessions
        if bool(query.mask(tail).iloc[-1]):
            result.matches.append(Match(symbol, latest.date(), {c: float(row[c]) for c in t.columns},
                                        describe(query.root, tail)))

    if query.order in ORDER_KEYS:
        column, descending = ORDER_KEYS[query.order]

        def sort_key(m: Match):
            value = m.values.get(column, float("nan"))
            missing = value != value
            return (missing, -value if descending and not missing else value if not missing else 0.0, m.symbol)

        result.matches.sort(key=sort_key)
    return result


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
