"""
QuantBIST
Elimination filters applied to every /tara result by default (profesyonel filtreler Aşama 1,
DECISIONS K-45). They remove stocks, they never pick one. Each can be turned off: ele=hayir
(all), ele_likidite=0 (or likidite=0, the older name), ele_kurumsal=0, ele_hareket=0, ele_veri=0.

- likidite: mean TL turnover of the PREVIOUS 20 full sessions < 15 mn TL (today not counted).
- kurumsal: a rights issue (bedelli), bonus issue or split (bedelsiz/bölünme) in
  data/corporate_actions.csv, or a listing (halka arz: first candle after the price store's
  start), in the last 60 sessions. A stock without a record is UNKNOWN, not eliminated.
- hareket: 3 or more daily moves beyond ±9.5% in the last 10 sessions, or ATR14/close in the top
  5% of the scanned list (only with at least MIN_FOR_RANK stocks; on 3 stocks it means nothing).
- veri: an unresolved ±20% one-day jump in the last 252 sessions (an unadjusted action; the
  52-week fields would be built across it), 3 or more zero-volume days in the last 20 sessions,
  or (live only) a second-source difference waiting for a correction.

The history card applies the same series day by day: each day sees only its own past.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

DEFAULT_LIQUIDITY = 15.0  # million TL
CORPORATE_WINDOW = 60
LIMIT_MOVE = 0.095
LIMIT_WINDOW, LIMIT_DAYS = 10, 3
ATR_TOP = 0.95
MIN_FOR_RANK = 20
JUMP, JUMP_WINDOW = 0.20, 252
ZERO_WINDOW, ZERO_DAYS = 20, 3
LISTING_GRACE = 5  # sessions after the store's first day that still count as "traded since the start"
KINDS = {"rights": "bedelli", "bonus": "bedelsiz/bölünme", "split": "bedelsiz/bölünme"}
NOTE = ("kurumsal işlem yalnız data/corporate_actions.csv'deki kayıtlardan bilinir; kaydı olmayan hissede "
        "bilinmiyor (elenmez)")
OPTIONS = ("ele", "ele_likidite", "ele_kurumsal", "ele_hareket", "ele_veri")


@dataclass(frozen=True)
class Settings:
    liquidity: float = DEFAULT_LIQUIDITY
    corporate: bool = True
    move: bool = True
    data: bool = True

    @classmethod
    def off(cls) -> Settings:
        return cls(0.0, False, False, False)

    def options(self) -> list[str]:
        """The non-default choices, as they are written (part of the criterion)."""

        from core.screen.language import _number

        if self == Settings.off():
            return ["ele=hayir"]
        out = []
        if self.liquidity != DEFAULT_LIQUIDITY:
            out.append(f"likidite={_number(self.liquidity)}")
        out += [f"ele_{name}=0" for name, on in (("kurumsal", self.corporate), ("hareket", self.move),
                                                  ("veri", self.data)) if not on]
        return out

    def with_option(self, name: str, value) -> Settings:
        if name == "ele":
            return self if value else Settings.off()
        if name in ("ele_likidite", "likidite"):
            return replace(self, liquidity=float(value))
        return replace(self, **{{"ele_kurumsal": "corporate", "ele_hareket": "move", "ele_veri": "data"}[name]: value})


def _dated(events: pd.Series, window: int) -> pd.Series:
    """'label dd.mm' on each event day and the window-1 sessions after it (the latest event wins)."""

    return events.where(events != "").replace("", np.nan).ffill(limit=window - 1).fillna("")


def frame(df: pd.DataFrame, symbol: str, store_index: pd.DatetimeIndex, actions) -> pd.DataFrame:
    """Per session: previous-20 liquidity, limit days, ATR%, and the corporate and data labels."""

    from core.strategy.score import average_true_range

    close, volume = df["close"], df["volume"]
    out = pd.DataFrame(index=df.index)
    out["liquidity"] = (close * volume).shift(1).rolling(20).mean() / 1e6
    move = (close / close.shift(1) - 1).abs()
    out["limit_days"] = (move > LIMIT_MOVE).astype(int).rolling(LIMIT_WINDOW, min_periods=1).sum()
    out["atr_pct"] = average_true_range(df["high"], df["low"], close, 14) / close * 100

    corporate = pd.Series("", index=df.index, dtype=object)
    for a in actions:
        if a.symbol != symbol or a.kind not in KINDS:
            continue
        at = df.index.searchsorted(pd.Timestamp(a.ex_date))
        if at < len(df.index):
            corporate.iloc[at] = f"{KINDS[a.kind]} {pd.Timestamp(a.ex_date):%d.%m}"
    if len(store_index) and len(df.index):
        start = store_index.searchsorted(df.index[0])
        if start > LISTING_GRACE:
            corporate.iloc[0] = corporate.iloc[0] or f"halka arz {df.index[0]:%d.%m}"
    out["corporate"] = _dated(corporate, CORPORATE_WINDOW)

    jumps = pd.Series("", index=df.index, dtype=object)
    jumped = move > JUMP
    jumps[jumped] = [f"veri: düzeltilmemiş sıçrama {d:%d.%m}" for d in df.index[jumped]]
    out["jump"] = _dated(jumps, JUMP_WINDOW)
    out["zero_days"] = (volume <= 0).astype(int).rolling(ZERO_WINDOW, min_periods=1).sum()
    return out


def reasons(row: pd.Series, settings: Settings, atr_cut: float | None = None, suspect: bool = False) -> list[str]:
    """Why one stock is eliminated on one session (empty: it stays)."""

    from core.reports.daily import tr

    found = []
    if settings.liquidity > 0 and not (row["liquidity"] >= settings.liquidity):
        value = row["liquidity"]
        found.append(f"likidite {tr(value, 0)} mn TL" if value == value else "likidite: 20 seans geçmiş yok")
    if settings.corporate and row["corporate"]:
        found.append(row["corporate"])
    if settings.move:
        if row["limit_days"] >= LIMIT_DAYS:
            found.append(f"{LIMIT_WINDOW} seansta {int(row['limit_days'])} tavan/taban")
        if atr_cut is not None and row["atr_pct"] == row["atr_pct"] and row["atr_pct"] > atr_cut:
            found.append(f"ATR %{tr(row['atr_pct'], 1)}, listenin en oynak %5'i")
    if settings.data:
        if row["jump"]:
            found.append(row["jump"])
        if row["zero_days"] >= ZERO_DAYS:
            found.append(f"veri: {ZERO_WINDOW} seansta {int(row['zero_days'])} gün sıfır hacim")
        if suspect:
            found.append("veri: ikinci kaynakta fark (düzeltme bekliyor)")
    return found


def atr_cut(values) -> float | None:
    """The ATR% line of the top 5%, or None when the list is too small to rank."""

    values = [v for v in values if v == v]
    if len(values) < MIN_FOR_RANK:
        return None
    return float(np.quantile(values, ATR_TOP))


def mask(table: pd.DataFrame, settings: Settings, cut: pd.Series | None) -> np.ndarray:
    """True on the sessions a stock is eliminated (the card's day-by-day version of `reasons`)."""

    out = np.zeros(len(table), dtype=bool)
    if settings.liquidity > 0:
        out |= ~(table["liquidity"] >= settings.liquidity).to_numpy()
    if settings.corporate:
        out |= (table["corporate"] != "").to_numpy()
    if settings.move:
        out |= (table["limit_days"] >= LIMIT_DAYS).to_numpy()
        if cut is not None:
            line = cut.reindex(table.index).to_numpy()
            out |= np.nan_to_num(table["atr_pct"].to_numpy() > line, nan=False).astype(bool)
    if settings.data:
        out |= ((table["jump"] != "") | (table["zero_days"] >= ZERO_DAYS)).to_numpy()
    return out


def daily_cut(tables: dict[str, pd.DataFrame], eligible: dict[str, np.ndarray] | None = None) -> pd.Series:
    """Each day's top-5% ATR% line over the stocks in the universe that day (NaN under MIN_FOR_RANK)."""

    panel = pd.DataFrame({s: t["atr_pct"].where(eligible[s]) if eligible else t["atr_pct"]
                          for s, t in tables.items()})
    counts = panel.notna().sum(axis=1)
    return panel.quantile(ATR_TOP, axis=1).where(counts >= MIN_FOR_RANK)


_ACTIONS: dict = {}


def corporate_actions() -> list:
    """data/corporate_actions.csv, read once per process (the bot restarts on an upgrade)."""

    if "rows" not in _ACTIONS:
        from core.market.corrections import load_corporate_actions

        _ACTIONS["rows"] = load_corporate_actions()
    return _ACTIONS["rows"]


__all__ = ["DEFAULT_LIQUIDITY", "NOTE", "OPTIONS", "Settings", "atr_cut", "corporate_actions", "daily_cut", "frame",
           "mask", "reasons"]
