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

3. Price fixes (optional, off by default)
   One-day wrong closes found by the second-source check
   (core.market.crosscheck --export): each row multiplies one day's close
   by `factor`. Used only after use_price_fixes(path) - the research
   report's --price-fixes option.

       symbol,date,factor,source,note

   A fix is used only if data/price_fix_approvals.csv approves that exact
   row (same symbol, date and factor, approved=true, with a source); any
   other row stops the whole file (PriceFixGateError). The file is checked
   and loaded from one private copy, so it cannot change in between.

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
APPROVALS_FILE = DATA_DIR / "price_fix_approvals.csv"
FACTOR_TOLERANCE = 1e-6  # crosscheck writes factors with 6 decimals

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


def load_corporate_actions(path=None, problems: list[str] | None = None) -> list[CorporateAction]:
    """
    Valid rows. An unreadable row is skipped (its stock's history stays unadjusted) and, when
    `problems` is given, described there so the daily report can show it.
    """

    path = path or CORPORATE_ACTIONS_FILE
    actions: list[CorporateAction] = []

    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
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
                except (KeyError, ValueError, AttributeError) as exc:
                    logger.warning("Bad corporate action row %s | %s", row, exc)
                    if problems is not None:
                        problems.append(
                            f"corporate_actions.csv satır {reader.line_num} okunamadı "
                            f"({(row.get('symbol') or '?').strip()}: {exc}); bu hissenin geçmiş fiyatları düzeltilmedi"
                        )
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

    if actions is None:
        actions = _actions_override if _actions_override is not None else load_corporate_actions()
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


_price_fixes: dict[str, dict[pd.Timestamp, float]] | None = None
_actions_override: list[CorporateAction] | None = None


def use_corporate_actions(actions: list[CorporateAction] | None) -> None:
    """Experiments only (core.backtest.scenarios): replace the corporate action list; None restores the file."""

    global _actions_override
    _actions_override = actions
    _clear_price_cache()


def _clear_price_cache() -> None:
    """Cached price histories carry the old corrections: drop them."""

    from core.market import data

    data.clear_cache()


def load_price_fixes(path) -> dict[str, dict[pd.Timestamp, float]]:
    fixes: dict[str, dict[pd.Timestamp, float]] = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            factor = float(row["factor"])
            if not 0.5 < factor < 2.0:
                raise ValueError(f"{path}: {row['symbol']} {row['date']} factor {factor} looks wrong")
            fixes.setdefault(row["symbol"].strip().upper(), {})[pd.Timestamp(row["date"])] = factor
    return fixes


class PriceFixGateError(ValueError):
    """A price fix file that is not fully approved in data/price_fix_approvals.csv."""


def _rows(path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fh)]


def _key(row: dict) -> tuple[str, pd.Timestamp]:
    return row["symbol"].upper(), pd.Timestamp(row["date"])


def _validate_price_fix_source(path, approvals=None) -> bool:
    """Every row of the fix file must be approved, with the same factor and a source."""

    approved: dict[tuple[str, pd.Timestamp], dict] = {}
    for row in _rows(approvals or APPROVALS_FILE):
        if _key(row) in approved:
            raise PriceFixGateError(f"Onay listesinde tekrar eden satır: {row['symbol']} {row['date']}")
        if row.get("approved", "").lower() == "true" and not row.get("source"):
            raise PriceFixGateError(f"Onaylı satırın kaynağı yok: {row['symbol']} {row['date']}")
        approved[_key(row)] = row

    fixes = _rows(path)
    if not fixes:
        raise PriceFixGateError("Boş düzeltme dosyası reddedildi.")
    keys = [_key(r) for r in fixes]
    if len(set(keys)) != len(keys):
        raise PriceFixGateError("Düzeltme dosyasında tekrar eden satır var.")

    missing = [k for k in keys if k not in approved]
    if missing:
        raise PriceFixGateError(f"ENGELLENDİ: {len(missing)} düzeltme onay listesinde yok.")
    for row, key in zip(fixes, keys):
        if abs(float(row["factor"]) - float(approved[key]["factor"])) > FACTOR_TOLERANCE:
            raise PriceFixGateError(f"Onaylanan çarpan farklı: {row['symbol']} {row['date']}")
    unapproved = sum(approved[k].get("approved", "").lower() != "true" for k in keys)
    if unapproved:
        raise PriceFixGateError(f"ENGELLENDİ: {unapproved} onaysız fiyat düzeltmesi.")
    return True


def use_price_fixes(path=None) -> int:
    """Turn price fixes on (path) or off (None). Returns the number of fixed days.

    The file is copied once; the copy is checked against the approval list and loaded, and
    only then does it replace the active fixes. On any error the previous state stays."""

    global _price_fixes
    if path is None:
        _price_fixes = None
    else:
        import shutil
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory(prefix="qb-price-fix-") as folder:
            snapshot = Path(folder) / "verified_fixes.csv"
            with open(path, "rb") as source, open(snapshot, "xb") as target:
                shutil.copyfileobj(source, target)
            _validate_price_fix_source(snapshot)
            loaded = load_price_fixes(snapshot)
        if not any(loaded.values()):
            raise PriceFixGateError("Boş düzeltme dosyası reddedildi.")
        _price_fixes = loaded
    _clear_price_cache()
    return sum(len(v) for v in (_price_fixes or {}).values())


def apply_price_fixes(df: pd.DataFrame, symbol: str, fixes=None) -> pd.DataFrame:
    fixes = (_price_fixes or {}) if fixes is None else fixes
    days = fixes.get(symbol.upper())
    if df.empty or not days:
        return df
    df = df.copy()
    for day, factor in days.items():
        if day in df.index:
            close = df.at[day, "close"] * factor
            df.at[day, "close"] = close
            df.at[day, "high"] = max(df.at[day, "high"], close)
            df.at[day, "low"] = min(df.at[day, "low"], close)
    return df


def clean(
    df: pd.DataFrame,
    symbol: str,
    actions: list[CorporateAction] | None = None,
) -> pd.DataFrame:
    """All corrections, in order (price fixes only when turned on)."""

    df = apply_corporate_actions(drop_cancelled_sessions(df), symbol, actions)
    return apply_price_fixes(df, symbol) if _price_fixes else df


__all__ = [
    "CANCELLED_SESSIONS",
    "CORPORATE_ACTIONS_FILE",
    "APPROVALS_FILE",
    "PriceFixGateError",
    "CorporateAction",
    "load_corporate_actions",
    "drop_cancelled_sessions",
    "apply_corporate_actions",
    "clean",
    "apply_price_fixes",
    "load_price_fixes",
    "use_price_fixes",
    "use_corporate_actions",
]
