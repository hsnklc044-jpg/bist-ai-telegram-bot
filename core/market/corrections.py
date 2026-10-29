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
from pathlib import Path

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


KINDS = ("factor", "bonus", "rights", "reduction_rights")


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
        if self.kind == "reduction_rights":  # capital cut (each share x factor), then rights at once (TSPOR 2025)
            before = raw.loc[raw.index < pd.Timestamp(self.ex_date), "close"]
            if before.empty:
                return None
            p = float(before.iloc[-1])
            return (self.factor * p + self.ratio * self.price) / ((1 + self.ratio) * p)
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
    seen: set[tuple] = set()

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
                    # validation M15: rows that would corrupt prices silently are refused with a reason
                    if not action.source and "source" in (reader.fieldnames or []):
                        raise ValueError("kaynak yok")
                    if action.ex_date.weekday() >= 5:
                        raise ValueError("tarih hafta sonu")
                    if (action.symbol, action.ex_date, kind) in seen:
                        raise ValueError("aynı hisse, tarih ve tür tekrar ediyor (iki kez uygulanırdı)")
                    if action.ratio is not None and action.ratio <= 0:
                        raise ValueError("oran pozitif olmalı")
                    if action.factor is not None and not 0 < action.factor < 20:
                        raise ValueError("katsayı 0 ile 20 arasında olmalı")
                    if kind in ("rights", "reduction_rights") and _number(row.get("price")) is None:
                        raise ValueError("bedelli fiyatı yazılmamış (1 TL varsayılmaz)")
                    if kind not in KINDS:
                        raise ValueError(f"unknown kind {kind!r}")
                    if kind == "factor" and not action.factor:
                        raise ValueError("kind=factor needs a factor")
                    if kind in ("bonus", "rights", "reduction_rights") and not action.ratio:
                        raise ValueError(f"kind={kind} needs a ratio")
                    if kind == "reduction_rights" and not action.factor:
                        raise ValueError("kind=reduction_rights needs the reduction multiplier in factor")
                    actions.append(action)
                    seen.add((action.symbol, action.ex_date, kind))
                except (KeyError, ValueError, AttributeError) as exc:
                    logger.warning("Bad corporate action row %s | %s", row, exc)
                    if problems is not None:
                        problems.append(
                            f"corporate_actions.csv satır {reader.line_num} okunamadı "
                            f"({(row.get('symbol') or '?').strip()}: {exc}); bu hissenin geçmiş fiyatları düzeltilmedi"
                        )
    except FileNotFoundError:
        if problems is not None:  # validation M15 D-7: never silent
            problems.append(f"{Path(path).name} bulunamadı; kurumsal işlem düzeltmesi yapılmadı (bölünme ve bedelsizler sahte "
                            "sıçrama gibi görünür)")

    return actions


CANDLE_EXCEPTIONS_FILE = DATA_DIR / "candle_exceptions.csv"
CANDLE_ACTIONS = ("drop", "real_move")


@dataclass(frozen=True)
class CandleException:
    """One candle a second source showed wrong (drop) or one ±20% move it showed real (real_move)."""

    symbol: str
    date: date
    action: str
    source: str
    note: str = ""


def load_candle_exceptions(path=None, problems: list[str] | None = None) -> list[CandleException]:
    """data/candle_exceptions.csv; a row without a known action or a source is skipped and named."""

    path = Path(path or CANDLE_EXCEPTIONS_FILE)
    if not path.exists():
        return []
    rows: list[CandleException] = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                item = CandleException(row["symbol"].strip().upper(), date.fromisoformat(row["date"].strip()),
                                       row["action"].strip(), (row.get("source") or "").strip(),
                                       (row.get("note") or "").strip())
                if item.action not in CANDLE_ACTIONS:
                    raise ValueError(f"unknown action {item.action!r}")
                if not item.source:
                    raise ValueError("no source")
                rows.append(item)
            except (KeyError, ValueError, AttributeError) as exc:
                if problems is not None:
                    problems.append(f"candle_exceptions.csv satır {reader.line_num} okunamadı: {exc}")
    return rows


def real_moves(symbol: str, rows: list[CandleException] | None = None) -> set[date]:
    rows = load_candle_exceptions() if rows is None else rows
    return {r.date for r in rows if r.symbol == symbol.upper() and r.action == "real_move"}


def apply_candle_exceptions(df: pd.DataFrame, symbol: str, rows: list[CandleException] | None = None) -> pd.DataFrame:
    """Drop the candles a second source showed broken (ASUZU 27.06.2022)."""

    rows = load_candle_exceptions() if rows is None else rows
    dropped = [pd.Timestamp(r.date) for r in rows if r.symbol == symbol.upper() and r.action == "drop"]
    if df.empty or not dropped:
        return df
    return df[~df.index.normalize().isin(pd.DatetimeIndex(dropped))]


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
        if pd.Timestamp(action.ex_date) > raw.index[-1]:
            continue  # not traded yet (validation M15 D-3): applied from its first session
        if _already_adjusted(raw, action, factor):
            continue
        before = df.index < pd.Timestamp(action.ex_date)
        df.loc[before, list(PRICE_COLUMNS)] *= factor
        df.loc[before, "volume"] /= factor

    return df


# BIST's ±10% session limit, rounded to the price tick (as core.market.quality.SESSION_LIMIT)
SESSION_LIMIT = 0.105
_double_adjusted: dict[tuple[str, str], str] = {}


def double_adjusted() -> dict[tuple[str, str], str]:
    """Actions left out because the provider already adjusted them, (symbol, ex_date) → reason."""

    return _double_adjusted


def _already_adjusted(raw: pd.DataFrame, action: CorporateAction, factor: float) -> bool:
    """
    Validation M15: the raw ex-date open is a normal session, but with the factor applied it would be
    beyond the limit. The provider has adjusted the history itself; a second adjustment would make a
    fake jump. Such an action is skipped and named.
    """

    ex = pd.Timestamp(action.ex_date)
    before, after = raw.loc[raw.index < ex, "close"], raw.loc[raw.index >= ex, "open"]
    if before.empty or after.empty or not before.iloc[-1]:
        return False
    gap = float(after.iloc[0]) / float(before.iloc[-1])
    adjusted_gap = gap / factor
    if abs(gap - 1) > SESSION_LIMIT or abs(adjusted_gap - 1) <= SESSION_LIMIT:
        return False
    text = (f"{action.symbol.removesuffix('.IS')} {action.ex_date:%d.%m.%Y} {action.kind}: veri zaten düzeltilmiş "
            f"görünüyor (ham açılış {gap - 1:+.1%}, düzeltmeyle {adjusted_gap - 1:+.1%} olurdu); uygulanmadı, "
            "data/corporate_actions.csv satırını kontrol edin")
    if (action.symbol, action.ex_date.isoformat()) not in _double_adjusted:
        logger.warning("Corporate action skipped (provider already adjusted) | %s", action)
    _double_adjusted[(action.symbol, action.ex_date.isoformat())] = text
    return True


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

    df = apply_corporate_actions(apply_candle_exceptions(drop_cancelled_sessions(df), symbol), symbol, actions)
    return apply_price_fixes(df, symbol) if _price_fixes else df


__all__ = [
    "CANCELLED_SESSIONS",
    "CANDLE_EXCEPTIONS_FILE",
    "CandleException",
    "apply_candle_exceptions",
    "load_candle_exceptions",
    "real_moves",
    "CORPORATE_ACTIONS_FILE",
    "APPROVALS_FILE",
    "PriceFixGateError",
    "CorporateAction",
    "load_corporate_actions",
    "drop_cancelled_sessions",
    "apply_corporate_actions",
    "clean",
    "double_adjusted",
    "apply_price_fixes",
    "load_price_fixes",
    "use_price_fixes",
    "use_corporate_actions",
]
