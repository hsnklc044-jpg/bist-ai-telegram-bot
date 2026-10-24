"""
QuantBIST
Backtest runner and report.

Runs the engine over the universe from the local price store. The
portfolio splits capital equally across the symbols at the start and
never rebalances, so it is the average of the per-symbol curves.

Prices are loaded once into a Dataset, so several rule sets can be
compared on exactly the same data (python -m core.backtest --compare).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field, replace

import pandas as pd

from core.backtest.engine import (
    BacktestConfig,
    SymbolResult,
    curve_stats,
    simulate,
    trade_stats,
)
from core.backtest.signals import score_history
from core.infrastructure.logger import get_logger
from core.market.data import load_price_history, preload
from core.market.quality import suspicious_jumps
from core.market.universe import BENCHMARK, load_universe

logger = get_logger(__name__)

PERIOD = "5y"
USDTRY = "TRY=X"
REGIME_WINDOW = 200

DISCLAIMER = (
    "Geçmiş performans geleceği garanti etmez. Temettü, bölünme ve "
    "bedelsiz düzeltmeleri veri sağlayıcısına bağlıdır. Yatırım tavsiyesi değildir."
)

TRAILING = BacktestConfig(target_atr=None, trailing_atr=3.0, max_hold_days=10_000)

VARIANTS: dict[str, BacktestConfig] = {
    "Hedef 4 ATR, 40 gün": BacktestConfig(),
    "İzleyen stop 3 ATR": TRAILING,
    "İzleyen 3 ATR + trendde tut": replace(TRAILING, hold_in_uptrend=True),
    "İzleyen 4 ATR + trendde tut": replace(TRAILING, trailing_atr=4.0, hold_in_uptrend=True),
}


# =====================================================
# DATA
# =====================================================


@dataclass
class Dataset:
    prices: dict[str, pd.DataFrame]
    signals: dict[str, pd.DataFrame]
    benchmark: pd.DataFrame | None
    usdtry: pd.Series | None
    skipped: dict[str, str] = field(default_factory=dict)

    @property
    def uptrend(self) -> pd.Series | None:
        """XU100 close above its 200-day average, known at each close."""

        if self.benchmark is None or len(self.benchmark) < REGIME_WINDOW:
            return None

        close = self.benchmark["close"]
        return close > close.rolling(REGIME_WINDOW).mean()


def _optional(symbol: str) -> pd.DataFrame | None:
    try:
        return load_price_history(symbol, period=PERIOD)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Optional series unavailable | %s | %s", symbol, exc)
        return None


def load_dataset(symbols: list[str] | None = None, exclude_jumps: bool = True) -> Dataset:
    """
    Load prices and signal histories.

    Symbols whose history has a jump the daily price limit cannot
    explain (usually an unadjusted bonus issue) are left out: a fake
    -60% day would be traded as a real loss or a real gain.
    """

    symbols = symbols or load_universe()
    preload([BENCHMARK, USDTRY, *symbols])

    prices: dict[str, pd.DataFrame] = {}
    skipped: dict[str, str] = {}

    for symbol in symbols:
        try:
            df = load_price_history(symbol, period=PERIOD)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Backtest skipped | %s | %s", symbol, exc)
            skipped[symbol] = "veri yok"
            continue

        jumps = suspicious_jumps(df) if exclude_jumps else pd.Series(dtype=float)

        if not jumps.empty:
            day, move = next(iter(jumps.items()))
            skipped[symbol] = f"düzeltilmemiş sıçrama {day.date()} {move:+.0%}"
            continue

        prices[symbol] = df

    fx = _optional(USDTRY)

    return Dataset(
        prices=prices,
        signals={s: score_history(df) for s, df in prices.items()},
        benchmark=_optional(BENCHMARK),
        usdtry=None if fx is None else fx["close"],
        skipped=skipped,
    )


# =====================================================
# PORTFOLIO
# =====================================================


@dataclass
class PortfolioResult:
    config: BacktestConfig
    results: list[SymbolResult]
    equity: pd.Series
    buy_hold_equity: pd.Series
    total_return: float
    cagr: float
    max_drawdown: float
    sharpe: float
    benchmark_return: float | None
    usd_return: float | None
    benchmark_usd_return: float | None
    halves: tuple[float, float]
    skipped: dict[str, str]
    usdtry: pd.Series | None = field(default=None, repr=False)

    @property
    def trades(self):
        return [t for r in self.results for t in r.trades]

    @property
    def exposure(self) -> float:
        return sum(r.metrics.exposure for r in self.results) / len(self.results)


def _period_return(curve: pd.Series) -> float:
    curve = curve.dropna()
    return float(curve.iloc[-1] / curve.iloc[0] - 1) if len(curve) > 1 else 0.0


def _usd_return(curve: pd.Series, usdtry: pd.Series | None) -> float | None:
    """Return of a TL curve measured in dollars."""

    if usdtry is None or usdtry.empty:
        return None

    fx = usdtry.sort_index()
    start, end = fx.asof(curve.index[0]), fx.asof(curve.index[-1])

    if pd.isna(start) or pd.isna(end):
        return None

    return float((1 + _period_return(curve)) * start / end - 1)


def _halves(curve: pd.Series) -> tuple[float, float]:
    middle = len(curve) // 2
    return _period_return(curve.iloc[: middle + 1]), _period_return(curve.iloc[middle:])


def run_portfolio(data: Dataset, config: BacktestConfig | None = None) -> PortfolioResult:
    config = config or BacktestConfig()

    if not data.prices:
        raise ValueError("Backtest için fiyat verisi olan hisse yok.")

    uptrend = data.uptrend
    results = [
        simulate(symbol, df, config, data.signals[symbol], uptrend)
        for symbol, df in data.prices.items()
    ]

    # Both curves start when the first signal can exist (after warm-up).
    start = min(
        r.signals["score"].first_valid_index() or r.equity.index[0] for r in results
    )

    curves = pd.concat([r.equity for r in results], axis=1).sort_index()
    equity = curves[curves.index >= start].ffill().fillna(1.0).mean(axis=1)
    equity = equity / equity.iloc[0]

    closes = pd.concat([df["close"] for df in data.prices.values()], axis=1).sort_index()
    closes = closes[closes.index >= start].ffill().bfill()
    buy_hold = (closes / closes.iloc[0]).mean(axis=1)

    total, cagr, drawdown, sharpe = curve_stats(equity)

    benchmark_return = benchmark_usd = None
    if data.benchmark is not None:
        bench = data.benchmark["close"]
        bench = bench[bench.index >= start]
        if len(bench) > 1:
            benchmark_return = _period_return(bench)
            benchmark_usd = _usd_return(bench, data.usdtry)

    return PortfolioResult(
        config=config,
        results=results,
        equity=equity,
        buy_hold_equity=buy_hold,
        total_return=total,
        cagr=cagr,
        max_drawdown=drawdown,
        sharpe=sharpe,
        benchmark_return=benchmark_return,
        usd_return=_usd_return(equity, data.usdtry),
        benchmark_usd_return=benchmark_usd,
        halves=_halves(equity),
        skipped=data.skipped,
        usdtry=data.usdtry,
    )


def run_universe(
    symbols: list[str] | None = None,
    config: BacktestConfig | None = None,
) -> PortfolioResult:
    return run_portfolio(load_dataset(symbols), config)


def run_symbol(symbol: str, config: BacktestConfig | None = None) -> SymbolResult:
    return simulate(symbol, load_price_history(symbol, period=PERIOD), config)


def compare(
    data: Dataset,
    variants: dict[str, BacktestConfig] | None = None,
) -> dict[str, PortfolioResult]:
    return {name: run_portfolio(data, config) for name, config in (variants or VARIANTS).items()}


# =====================================================
# FORMATTING
# =====================================================


def _pct(value: float | None) -> str:
    return "-" if value is None else f"%{value * 100:.1f}"


def _pf(value: float) -> str:
    return "∞" if math.isinf(value) else f"{value:.2f}"


def _rules(c: BacktestConfig) -> str:
    exits = [f"stop {c.stop_atr:g} ATR"]
    if c.target_atr:
        exits.append(f"hedef {c.target_atr:g} ATR")
    if c.trailing_atr:
        exits.append(f"izleyen stop {c.trailing_atr:g} ATR")
    if c.max_hold_days < 10_000:
        exits.append(f"en fazla {c.max_hold_days} gün")
    if c.hold_in_uptrend:
        exits.append("XU100 200 günlük ortalamanın üstündeyken sat sinyali yok sayılır")

    text = (
        f"Kurallar: skor ≥ {c.entry_score:g} al (ertesi açılış), skor ≤ {c.exit_score:g} sat, "
        + ", ".join(exits)
        + f". Komisyon %{c.commission * 100:g}, kayma %{c.slippage * 100:g} (her işlem yönü)."
    )
    if c.cash_rate:
        text += f" Boştaki nakit yıllık %{c.cash_rate * 100:g} faiz alır."

    return text


def _skipped(skipped: dict[str, str]) -> list[str]:
    if not skipped:
        return []

    return ["", "Dışarıda bırakılan:"] + [f"- {s}: {why}" for s, why in skipped.items()]


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

    lines = [
        "🧪 QUANTBIST BACKTEST",
        f"📅 {result.equity.index[0].date()} → {result.equity.index[-1].date()}"
        f" | {len(result.results)} hisse",
        "",
        f"💰 Portföy getirisi : {_pct(result.total_return)} (USD {_pct(result.usd_return)})",
        f"📦 Aynı hisseler al-tut : {_pct(_period_return(result.buy_hold_equity))}",
        f"📦 XU100 al-tut : {_pct(result.benchmark_return)}"
        f" (USD {_pct(result.benchmark_usd_return)})",
        f"📈 Yıllık (CAGR) : {_pct(result.cagr)}",
        f"📉 En büyük düşüş : {_pct(result.max_drawdown)}",
        f"⚖️ Sharpe : {result.sharpe:.2f}",
        f"🕒 Piyasada kalma : {_pct(result.exposure)}",
        f"🪓 1. yarı / 2. yarı : {_pct(result.halves[0])} / {_pct(result.halves[1])}",
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

    lines += _skipped(result.skipped)
    lines += ["", _rules(result.config), "", f"⚠️ {DISCLAIMER}"]

    return "\n".join(lines)


def format_comparison(results: dict[str, PortfolioResult]) -> str:
    any_result = next(iter(results.values()))
    header = (
        f"{'Kural seti':<28} {'TL':>8} {'USD':>7} {'CAGR':>7} {'MaxDD':>7} "
        f"{'Sharpe':>6} {'İşlem':>5} {'Piyasa':>6} {'1.yarı':>7} {'2.yarı':>7}"
    )

    lines = [
        "🧪 KURAL SETİ KARŞILAŞTIRMASI",
        f"📅 {any_result.equity.index[0].date()} → {any_result.equity.index[-1].date()}"
        f" | {len(any_result.results)} hisse",
        "",
        header,
    ]

    for name, r in results.items():
        lines.append(
            f"{name:<28} {_pct(r.total_return):>8} {_pct(r.usd_return):>7} "
            f"{_pct(r.cagr):>7} {_pct(r.max_drawdown):>7} {r.sharpe:>6.2f} "
            f"{len(r.trades):>5} {_pct(r.exposure):>6} "
            f"{_pct(r.halves[0]):>7} {_pct(r.halves[1]):>7}"
        )

    bh = any_result.buy_hold_equity
    bh_total, bh_cagr, bh_dd, bh_sharpe = curve_stats(bh)
    bh_halves = _halves(bh)
    lines.append(
        f"{'Aynı hisseler al-tut':<28} {_pct(bh_total):>8} "
        f"{_pct(_usd_return(bh, any_result.usdtry)):>7} {_pct(bh_cagr):>7} {_pct(bh_dd):>7} "
        f"{bh_sharpe:>6.2f} {'-':>5} {'%100.0':>6} {_pct(bh_halves[0]):>7} {_pct(bh_halves[1]):>7}"
    )
    lines.append(
        f"{'XU100 al-tut':<28} {_pct(any_result.benchmark_return):>8} "
        f"{_pct(any_result.benchmark_usd_return):>7}"
    )

    lines += _skipped(any_result.skipped)
    lines += [
        "",
        "Not: Birkaç kural seti denendiğinde en iyisi şans eseri iyi görünebilir;",
        "iki yarıda da tutarlı olan kural seti daha güvenilirdir.",
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
    "VARIANTS",
    "Dataset",
    "PortfolioResult",
    "compare",
    "format_comparison",
    "format_portfolio",
    "format_symbol",
    "format_trades",
    "load_dataset",
    "run_portfolio",
    "run_symbol",
    "run_universe",
]
