"""
QuantBIST
Momentum rotation, live.

The strategy that held up in the backtest (python -m core.backtest
--compare): after the close of the first session of each month, rank
the universe by 126-session return and hold the top 5 in equal weight
from the next open. This module computes today's ranking, the backtest
summary shown next to it, and the monthly "what changes" notice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from core.backtest.engine import curve_stats
from core.backtest.rotation import RotationConfig, current_picks, rotate
from core.backtest.runner import (
    DISCLAIMER,
    Dataset,
    buy_hold_curve,
    comparison_start,
    load_dataset,
    usd_return,
)
from core.config.paths import ROTATION_STATE_FILE
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

STRATEGY = RotationConfig(ranking="momentum", top_n=5)
RESERVES = 5


@dataclass
class Pick:
    symbol: str
    momentum: float
    price: float


@dataclass
class BacktestSummary:
    start: date
    total_return: float
    usd_return: float | None
    max_drawdown: float
    buy_hold_return: float
    buy_hold_usd_return: float | None
    buy_hold_drawdown: float


@dataclass
class RotationReport:
    as_of: date
    picks: list[Pick]
    reserves: list[Pick]
    rebalance_today: bool
    next_rebalance: date
    backtest: BacktestSummary | None
    skipped: dict[str, str] = field(default_factory=dict)

    @property
    def symbols(self) -> list[str]:
        return [p.symbol for p in self.picks]


def next_rebalance_day(today: date) -> date:
    """First business day of the next month (holidays not known here)."""

    first = (pd.Timestamp(today) + pd.offsets.MonthBegin(1)).date()
    return pd.offsets.BDay().rollforward(pd.Timestamp(first)).date()


def _backtest(data: Dataset) -> BacktestSummary | None:
    try:
        start = comparison_start(data, {"live": STRATEGY})
        equity = rotate(data.prices, data.signals, STRATEGY, data.uptrend, start).equity
        buy_hold = buy_hold_curve(data, start)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Rotation backtest failed | %s", exc)
        return None

    total, _, drawdown, _ = curve_stats(equity)
    bh_total, _, bh_drawdown, _ = curve_stats(buy_hold)

    return BacktestSummary(
        start=start.date(),
        total_return=total,
        usd_return=usd_return(equity, data.usdtry),
        max_drawdown=drawdown,
        buy_hold_return=bh_total,
        buy_hold_usd_return=usd_return(buy_hold, data.usdtry),
        buy_hold_drawdown=bh_drawdown,
    )


def build_report(data: Dataset | None = None, with_backtest: bool = True) -> RotationReport:
    data = data or load_dataset()

    if not data.prices:
        raise ValueError("Rotasyon için fiyat verisi olan hisse yok.")

    ranking = current_picks(data.prices, data.signals, STRATEGY)
    calendar = pd.concat([df["close"] for df in data.prices.values()], axis=1).sort_index().index
    as_of = calendar[-1]

    def pick(symbol: str) -> Pick:
        return Pick(
            symbol=symbol,
            momentum=float(ranking[symbol]),
            price=round(float(data.prices[symbol]["close"].iloc[-1]), 2),
        )

    symbols = list(ranking.index)
    rebalance_today = len(calendar) > 1 and as_of.month != calendar[-2].month

    return RotationReport(
        as_of=as_of.date(),
        picks=[pick(s) for s in symbols[: STRATEGY.top_n]],
        reserves=[pick(s) for s in symbols[STRATEGY.top_n : STRATEGY.top_n + RESERVES]],
        rebalance_today=rebalance_today,
        next_rebalance=as_of.date() if rebalance_today else next_rebalance_day(as_of.date()),
        backtest=_backtest(data) if with_backtest else None,
        skipped=data.skipped,
    )


# =====================================================
# FORMATTING
# =====================================================


def _pct(value: float | None) -> str:
    return "-" if value is None else f"%{value * 100:+.1f}"


def _code(symbol: str) -> str:
    return symbol.removesuffix(".IS")


def format_report(report: RotationReport) -> str:
    lines = [
        "🔄 MOMENTUM ROTASYONU",
        f"📅 {report.as_of} kapanışına göre",
        "",
        f"En güçlü {STRATEGY.top_n} (6 aylık getiri):",
    ]

    for i, p in enumerate(report.picks, start=1):
        lines.append(f"{i}. {_code(p.symbol):<6} {_pct(p.momentum):>8}   {p.price} TL")

    if report.reserves:
        lines += ["", "Sıradakiler: " + ", ".join(_code(p.symbol) for p in report.reserves)]

    lines.append("")
    if report.rebalance_today:
        lines.append("🗓 Bugün dengeleme günü: liste yarın açılışta uygulanır.")
    else:
        lines.append(
            f"🗓 Sonraki dengeleme: {report.next_rebalance} kapanışı (ayın ilk seansı)."
        )

    b = report.backtest
    if b:
        lines += [
            "",
            f"🧪 Backtest ({b.start} →, aylık, eşit ağırlık, maliyetler dahil):",
            f"Rotasyon : {_pct(b.total_return)} TL / {_pct(b.usd_return)} USD,"
            f" en büyük düşüş {_pct(b.max_drawdown)}",
            f"Al-tut   : {_pct(b.buy_hold_return)} TL / {_pct(b.buy_hold_usd_return)} USD,"
            f" en büyük düşüş {_pct(b.buy_hold_drawdown)}",
        ]

    if report.skipped:
        lines += ["", "Veri sorunu nedeniyle dışarıda: " + ", ".join(map(_code, report.skipped))]

    lines += [
        "",
        "⚠️ Hisse listesi bugünün büyük şirketlerinden oluşur; bu, backtesti iyimser gösterir.",
        f"⚠️ {DISCLAIMER}",
    ]

    return "\n".join(lines)


def format_rebalance(report: RotationReport, previous: list[str]) -> str:
    new = report.symbols
    added = [s for s in new if s not in previous]
    removed = [s for s in previous if s not in new]
    kept = [s for s in new if s in previous]

    def codes(symbols: list[str]) -> str:
        return ", ".join(map(_code, symbols)) or "-"

    lines = [
        "🔄 AYLIK DENGELEME",
        f"📅 {report.as_of} kapanışına göre, yarın açılışta uygulanır.",
        "",
        f"➕ Giren : {codes(added)}",
        f"➖ Çıkan : {codes(removed)}",
        f"⏸ Kalan : {codes(kept)}",
        "",
        f"Yeni liste (her biri %{100 / max(len(new), 1):.0f}): {codes(new)}",
    ]

    if not previous:
        lines += ["", "İlk bildirim: önceki liste kayıtlı değildi."]

    lines += ["", "Ayrıntı: /rotasyon", f"⚠️ {DISCLAIMER}"]

    return "\n".join(lines)


# =====================================================
# MONTHLY NOTICE
# =====================================================


def load_state() -> dict:
    try:
        return json.loads(ROTATION_STATE_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        logger.warning("Rotation state unreadable, starting fresh | %s", exc)
        return {}


def save_state(as_of: date, holdings: list[str]) -> None:
    ROTATION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ROTATION_STATE_FILE.write_text(
        json.dumps({"as_of": as_of.isoformat(), "holdings": holdings}, indent=2),
        encoding="utf-8",
    )


def check_rebalance(data: Dataset | None = None) -> str | None:
    """
    The rebalance notice when the latest candle is the first session of
    a month and it has not been sent yet; otherwise None.
    """

    report = build_report(data, with_backtest=False)

    if not report.rebalance_today:
        return None

    state = load_state()

    if state.get("as_of") == report.as_of.isoformat():
        return None

    message = format_rebalance(report, state.get("holdings", []))
    save_state(report.as_of, report.symbols)

    return message


__all__ = [
    "STRATEGY",
    "Pick",
    "RotationReport",
    "build_report",
    "check_rebalance",
    "format_rebalance",
    "format_report",
    "next_rebalance_day",
]
