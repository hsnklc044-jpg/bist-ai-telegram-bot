"""
QuantBIST
Backtest runner and report.

Runs the engine over the universe from the local price store. The
portfolio splits capital equally across the symbols at the start and
never rebalances, so it is the average of the per-symbol curves.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

import pandas as pd

from core.backtest.engine import (
    BacktestConfig,
    SymbolResult,
    curve_stats,
    simulate,
    trade_stats,
)
from core.infrastructure.logger import get_logger
from core.market.data import load_price_history, preload
from core.market.universe import BENCHMARK, load_universe

logger = get_logger(__name__)

PERIOD = "5y"

DISCLAIMER = (
    "Geçmiş performans geleceği garanti etmez. Temettü, bölünme ve "
    "bedelsiz düzeltmeleri veri sağlayıcısına bağlıdır. Yatırım tavsiyesi değildir."
)


@dataclass
class PortfolioResult:
    config: BacktestConfig
    results: list[SymbolResult]
    equity: pd.Series
    total_return: float
    cagr: float
    max_drawdown: float
    sharpe: float
    benchmark_return: float | None
    skipped: list[str]

    @property
    def trades(self):
        return [t for r in self.results for t in r.trades]


def run_symbol(symbol: str, config: BacktestConfig | None = None) -> SymbolResult:
    return simulate(symbol, load_price_history(symbol, period=PERIOD), config)


def _benchmark_return(start: pd.Timestamp) -> float | None:
    try:
        df = load_price_history(BENCHMARK, period=PERIOD)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Benchmark unavailable | %s", exc)
        return None

    df = df[df.index >= start]

    if len(df) < 2:
        return None

    return float(df["close"].iloc[-1] / df["close"].iloc[0] - 1)


def run_universe(
    symbols: list[str] | None = None,
    config: BacktestConfig | None = None,
) -> PortfolioResult:
    config = config or BacktestConfig()
    symbols = symbols or load_universe()

    preload([BENCHMARK, *symbols])

    results: list[SymbolResult] = []
    skipped: list[str] = []

    for symbol in symbols:
        try:
            results.append(run_symbol(symbol, config))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Backtest skipped | %s | %s", symbol, exc)
            skipped.append(symbol)

    if not results:
        raise ValueError("Backtest için fiyat verisi olan hisse yok.")

    curves = pd.concat([r.equity for r in results], axis=1).sort_index()
    equity = curves.ffill().fillna(1.0).mean(axis=1)

    total, cagr, drawdown, sharpe = curve_stats(equity)

    first_signal = min(
        r.signals["score"].first_valid_index() or r.equity.index[0] for r in results
    )

    return PortfolioResult(
        config=config,
        results=results,
        equity=equity,
        total_return=total,
        cagr=cagr,
        max_drawdown=drawdown,
        sharpe=sharpe,
        benchmark_return=_benchmark_return(first_signal),
        skipped=skipped,
    )


# =====================================================
# FORMATTING
# =====================================================


def _pct(value: float | None) -> str:
    return "-" if value is None else f"%{value * 100:.1f}"


def _pf(value: float) -> str:
    return "∞" if math.isinf(value) else f"{value:.2f}"


def format_symbol(result: SymbolResult) -> str:
    m = result.metrics
    first = result.equity.index[0].date()
    last = result.equity.index[-1].date()
    reasons = Counter(t.reason for t in result.trades)

    return "\n".join(
        [
            f"🧪 BACKTEST {result.symbol}",
            f"📅 {first} → {last}",
            "",
            f"💰 Strateji getirisi : {_pct(m.total_return)}",
            f"📦 Al-tut getirisi : {_pct(m.buy_hold)}",
            f"📈 Yıllık (CAGR) : {_pct(m.cagr)}",
            f"📉 En büyük düşüş : {_pct(m.max_drawdown)}",
            f"⚖️ Sharpe : {m.sharpe:.2f}",
            "",
            f"🔁 İşlem sayısı : {m.trades}",
            f"✅ Kazanma oranı : {_pct(m.win_rate)}",
            f"➗ Ortalama işlem : {_pct(m.avg_trade)}",
            f"🏦 Kâr faktörü : {_pf(m.profit_factor)}",
            f"⏱ Ortalama süre : {m.avg_days:.1f} gün",
            f"🕒 Piyasada kalma : {_pct(m.exposure)}",
            "",
            "Çıkışlar: "
            + (", ".join(f"{k} {v}" for k, v in sorted(reasons.items())) or "-"),
        ]
    )


def format_portfolio(result: PortfolioResult, top: int | None = None) -> str:
    stats = trade_stats(result.trades, result.config)
    c = result.config

    lines = [
        "🧪 QUANTBIST BACKTEST",
        f"📅 {result.equity.index[0].date()} → {result.equity.index[-1].date()}"
        f" | {len(result.results)} hisse",
        "",
        f"💰 Portföy getirisi : {_pct(result.total_return)}",
        f"📦 XU100 al-tut : {_pct(result.benchmark_return)}",
        f"📈 Yıllık (CAGR) : {_pct(result.cagr)}",
        f"📉 En büyük düşüş : {_pct(result.max_drawdown)}",
        f"⚖️ Sharpe : {result.sharpe:.2f}",
        "",
        f"🔁 İşlem sayısı : {stats['trades']}",
        f"✅ Kazanma oranı : {_pct(stats['win_rate'])}",
        f"➗ Ortalama işlem : {_pct(stats['avg_trade'])}",
        f"🏦 Kâr faktörü : {_pf(stats['profit_factor'])}",
        "",
        "Hisse bazında (strateji / al-tut, işlem):",
    ]

    ranked = sorted(result.results, key=lambda r: r.metrics.total_return, reverse=True)

    for r in ranked[:top] if top else ranked:
        m = r.metrics
        lines.append(
            f"{r.symbol.removesuffix('.IS'):<6} {_pct(m.total_return):>7} / "
            f"{_pct(m.buy_hold):>7}  {m.trades} işlem"
        )

    if result.skipped:
        lines += ["", "Verisi olmayan: " + ", ".join(result.skipped)]

    lines += [
        "",
        f"Kurallar: skor ≥ {c.entry_score:g} al (ertesi açılış), skor ≤ {c.exit_score:g} sat, "
        f"stop {c.stop_atr:g} ATR, hedef {c.target_atr:g} ATR, en fazla {c.max_hold_days} gün. "
        f"Komisyon %{c.commission * 100:g}, kayma %{c.slippage * 100:g} (her işlem yönü).",
        "",
        f"⚠️ {DISCLAIMER}",
    ]

    return "\n".join(lines)


def format_trades(result: SymbolResult, limit: int = 20) -> str:
    lines = ["Giriş       Çıkış         Giriş F.  Çıkış F.    Brüt   Gün  Neden"]

    for t in result.trades[-limit:]:
        lines.append(
            f"{t.entry_date.date()}  {t.exit_date.date()}  {t.entry_price:9.2f} "
            f"{t.exit_price:9.2f} {_pct(t.gross_return):>7} {t.days:4d}  {t.reason}"
        )

    return "\n".join(lines)


__all__ = [
    "DISCLAIMER",
    "PortfolioResult",
    "format_portfolio",
    "format_symbol",
    "format_trades",
    "run_symbol",
    "run_universe",
]
