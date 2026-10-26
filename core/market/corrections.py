"""
QuantBIST
Price corrections applied on top of the raw provider data.

1. Cancelled sessions
   Borsa Istanbul annulled every trade made on 8 February 2023 (after
   the Kahramanmaraş earthquakes) and closed until 14 February. Yahoo
   still carries candles for that day for most stocks, which turns the
   15 February reopening into a fake +15-22% jump.

2. Corporate actions (data/corporate_actions.csv)
   Yahoo does not always adjust BIST prices for bonus issues, rights
   issues or splits. Each row back-adjusts prices before `ex_date`:

       symbol,ex_date,factor,note
       HEKTS.IS,2024-09-09,0.3515,bedelsiz %184.5 (KAP ile doğrula)

   factor = new share count / old share count, inverted (price after /
   price before, without the market move). Prices before ex_date are
   multiplied by factor, volumes divided by it.

The raw data in the store is never modified; corrections are applied
when data is read, so a wrong row in the CSV can simply be removed.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date

import pandas as pd

from core.config.paths import DATA_DIR
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

CORPORATE_ACTIONS_FILE = DATA_DIR / "corporate_actions.csv"

CANCELLED_SESSIONS: frozenset[date] = frozenset(
    {
        date(2023, 2, 8),
    }
)

PRICE_COLUMNS = ("open", "high", "low", "close")


KINDS = ("factor", "bonus", "rights")


@dataclass(frozen=True)
class CorporateAction:
    symbol: str
    ex_date: date
    factor: float | None = None
    note: str = ""
    kind: str = "factor"
    ratio: float | None = None
    price: float = 1.0
    source: str = ""

    def resolve(self, raw: pd.DataFrame) -> float | None:
        """The price factor for this action, from the raw (unadjusted) candles."""

        if self.kind == "bonus":
            return 1 / (1 + self.ratio)
        if self.kind == "rights":
            before = raw.loc[raw.index < pd.Timestamp(self.ex_date), "close"]
            if before.empty:
                return None
            p = float(before.iloc[-1])
            return (p + self.ratio * self.price) / ((1 + self.ratio) * p)
        return self.factor


def _number(value) -> float | None:
    value = (value or "").strip()
    return float(value) if value else None


def load_corporate_actions(path=None) -> list[CorporateAction]:
    path = path or CORPORATE_ACTIONS_FILE
    actions: list[CorporateAction] = []

    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    kind = (row.get("kind") or "factor").strip().lower()
                    action = CorporateAction(
                        symbol=row["symbol"].strip().upper(),
                        ex_date=date.fromisoformat(row["ex_date"].strip()),
                        factor=_number(row.get("factor")),
                        note=(row.get("note") or "").strip(),
                        kind=kind,
                        ratio=_number(row.get("ratio")),
                        price=_number(row.get("price")) or 1.0,
                        source=(row.get("source") or "").strip(),
                    )
                    if kind not in KINDS:
                        raise ValueError(f"unknown kind {kind!r}")
                    if kind == "factor" and not action.factor:
                        raise ValueError("kind=factor needs a factor")
                    if kind in ("bonus", "rights") and not action.ratio:
                        raise ValueError(f"kind={kind} needs a ratio")
                    actions.append(action)
                except (KeyError, ValueError) as exc:
                    logger.warning("Bad corporate action row %s | %s", row, exc)
    except FileNotFoundError:
        pass

    return actions


def drop_cancelled_sessions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    cancelled = pd.DatetimeIndex([pd.Timestamp(d) for d in CANCELLED_SESSIONS])

    return df[~df.index.normalize().isin(cancelled)]


def apply_corporate_actions(
    df: pd.DataFrame,
    symbol: str,
    actions: list[CorporateAction] | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df

    actions = load_corporate_actions() if actions is None else actions
    relevant = [a for a in actions if a.symbol == symbol]

    if not relevant:
        return df

    raw = df
    df = df.copy()

    for action in relevant:
        factor = action.resolve(raw)
        if not factor:
            logger.warning("Corporate action skipped (no factor) | %s", action)
            continue
        before = df.index < pd.Timestamp(action.ex_date)
        df.loc[before, list(PRICE_COLUMNS)] *= factor
        df.loc[before, "volume"] /= factor

    return df


def clean(
    df: pd.DataFrame,
    symbol: str,
    actions: list[CorporateAction] | None = None,
) -> pd.DataFrame:
    """All corrections, in order."""

    return apply_corporate_actions(drop_cancelled_sessions(df), symbol, actions)


__all__ = [
    "CANCELLED_SESSIONS",
    "CORPORATE_ACTIONS_FILE",
    "CorporateAction",
    "load_corporate_actions",
    "drop_cancelled_sessions",
    "apply_corporate_actions",
    "clean",
]
