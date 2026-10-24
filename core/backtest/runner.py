"""
QuantBIST
Backtest runner and report.

Runs the engine over the universe from the local price store. The
portfolio splits capital equally across the symbols at the start and
never rebalances, so it is the average of the per-symbol curves.

Prices are loaded once into a Dataset, so several rule sets, including
the rotation strategy (rotation.py), can be compared on exactly the same
data and period (python -m core.backtest --compare).
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
from core.backtest.rotation import RotationConfig, rotate
from core.backtest.signals import score_history
from core.infrastructure.logger import get_logger
from core.market.data import load_price_history, preload
from core.market.indicators import MIN_HISTORY_LENGTH
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

ROTATIONS: dict[str, RotationConfig] = {
    "Rotasyon skor, ilk 5": RotationConfig(ranking="score"),
    "Rotasyon momentum, ilk 5": RotationConfig(ranking="momentum"),
    "Rotasyon karma, ilk 5": RotationConfig(),
    "Rotasyon karma, ilk 10": RotationConfig(top_n=10),
    "Rotasyon karma 5 + trend": RotationConfig(regime_filter=True),
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


def buy_hold_curve(data: Dataset, start: pd.Timestamp) -> pd.Series:
    """
    Equal-weight buy & hold from `start`, never rebalanced.

    Only stocks that already trade on `start` are bought; a later
    listing cannot be bought at a price it did not have yet.
    """

    closes = pd.concat([df["close"] for df in data.prices.values()], axis=1).sort_index()
    closes = closes[closes.index >= start].ffill()
    closes = closes.loc[:, closes.iloc[0].notna()]

    return (closes / closes.iloc[0]).mean(axis=1)


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

    buy_hold = buy_hold_curve(data, start)

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


@dataclass
class Line:
    """One row of a comparison: an equity curve plus optional trade facts."""

    name: str
    equity: pd.Series
    trades: int | None = None
    exposure: float | None = None


def comparison_start(data: Dataset, rotations: dict[str, RotationConfig]) -> pd.Timestamp:
    """First day every strategy in the comparison can already act on."""

    calendar = pd.concat([df["close"] for df in data.prices.values()], axis=1).sort_index().index
    warm_up = max([MIN_HISTORY_LENGTH] + [c.momentum_days for c in rotations.values()])

    return calendar[min(warm_up, len(calendar) - 2)]


def compare(
    data: Dataset,
    variants: dict[str, BacktestConfig] | None = None,
    rotations: dict[str, RotationConfig] | None = None,
) -> list[Line]:
    """
    Every rule set on the same data, rebased to one common start so
    the rows are comparable. Ends with the two buy & hold benchmarks.
    """

    if not data.prices:
        raise ValueError("Backtest için fiyat verisi olan hisse yok.")

    variants = VARIANTS if variants is None else variants
    rotations = ROTATIONS if rotations is None else rotations
    start = comparison_start(data, rotations)
    uptrend = data.uptrend

    lines = []

    for name, config in variants.items():
        r = run_portfolio(data, config)
        lines.append(Line(name, r.equity, len(r.trades), r.exposure))

    for name, config in rotations.items():
        r = rotate(data.prices, data.signals, config, uptrend, start)
        lines.append(Line(name, r.equity, r.trades, r.exposure))

    lines.append(Line("Aynı hisseler al-tut", buy_hold_curve(data, start), exposure=1.0))

    if data.benchmark is not None:
        lines.append(Line("XU100 al-tut", data.benchmark["close"], exposure=1.0))

    for line in lines:
        curve = line.equity[line.equity.index >= start].dropna()
        line.equity = curve / curve.iloc[0]

    return lines


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


def format_comparison(lines: list[Line], data: Dataset) -> str:
    first = lines[0].equity.index
    header = (
        f"{'Strateji':<28} {'TL':>8} {'USD':>7} {'CAGR':>7} {'MaxDD':>7} "
        f"{'Sharpe':>6} {'İşlem':>5} {'Piyasa':>6} {'1.yarı':>7} {'2.yarı':>7}"
    )

    out = [
        "🧪 STRATEJİ KARŞILAŞTIRMASI",
        f"📅 {first[0].date()} → {first[-1].date()} | {len(data.prices)} hisse",
        "",
        header,
    ]

    for line in lines:
        total, cagr, drawdown, sharpe = curve_stats(line.equity)
        h1, h2 = _halves(line.equity)
        trades = "-" if line.trades is None else str(line.trades)
        out.append(
            f"{line.name:<28} {_pct(total):>8} {_pct(_usd_return(line.equity, data.usdtry)):>7} "
            f"{_pct(cagr):>7} {_pct(drawdown):>7} {sharpe:>6.2f} {trades:>5} "
            f"{_pct(line.exposure):>6} {_pct(h1):>7} {_pct(h2):>7}"
        )

    out += _skipped(data.skipped)
    out += [
        "",
        "Zamanlama: skor ≥ 70 al / ≤ 35 sat (bkz. python -m core.backtest).",
        "Rotasyon: her 21 seansta en iyi N hisse eşit ağırlıkla tutulur; skor = /analyze skoru,",
        "momentum = 126 seanslık getiri, karma = ikisinin sıra ortalaması,",
        "trend = XU100 200 günlük ortalamanın altındayken nakit.",
        "Not: Birçok kural denendiğinde en iyisi şans eseri iyi görünebilir;",
        "iki yarıda da tutarlı olan daha güvenilirdir. Hisse listesi bugünün",
        "büyük şirketlerinden oluşur; bu, al-tut dahil her satırı iyimser gösterir.",
        "",
        f"⚠️ {DISCLAIMER}",
    ]

    return "\n".join(out)


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
    "ROTATIONS",
    "VARIANTS",
    "Dataset",
    "Line",
    "buy_hold_curve",
    "comparison_start",
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
