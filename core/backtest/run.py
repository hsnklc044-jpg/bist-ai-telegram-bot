"""
QuantBIST
Run the standard backtest report on the local price store.

    python -m core.backtest.run
    python -m core.backtest.run --positions 3 --start 2023-01-01

Uses the stored, corrected, closed candles (run `python -m core.market.update`
first). Symbols with unresolved data jumps are left out, because an
unadjusted bonus issue would look like a -60% trade.
"""

from __future__ import annotations

import argparse

import pandas as pd

from core.backtest.engine import BacktestConfig, buy_and_hold, compute_metrics, run_backtest
from core.market import store
from core.market.calendar import drop_open_candle
from core.market.corrections import clean
from core.market.quality import build_report
from core.market.universe import BENCHMARK, load_universe
from core.strategy.rules import score_rule, trend_rule

WARMUP_START = "2022-08-01"


def load_frames(symbols: list[str]) -> dict[str, pd.DataFrame]:
    return {s: drop_open_candle(clean(store.read(s), s)) for s in symbols}


def tradable_symbols(universe: list[str] | None = None) -> tuple[list[str], list[str]]:
    universe = universe or load_universe()
    report = {q.symbol: q for q in build_report(universe)}
    keep, skip = [], []

    for symbol in universe:
        q = report.get(symbol)
        if q is None or q.candles < 300 or q.jumps:
            skip.append(symbol)
        else:
            keep.append(symbol)

    return keep, skip


def yearly_returns(equity: pd.Series) -> pd.Series:
    yearly = equity.resample("YE").last()
    first = equity.iloc[0]
    return yearly.pct_change().fillna(yearly.iloc[0] / first - 1)


def run_report(
    positions: int = 5,
    start: str = WARMUP_START,
    end: str | None = None,
    commission: float = 0.001,
    slippage: float = 0.0005,
) -> str:
    symbols, skipped = tradable_symbols()
    frames = load_frames(symbols)
    bench = load_frames([BENCHMARK])[BENCHMARK]

    config = BacktestConfig(max_positions=positions, commission=commission, slippage=slippage)

    strategies = {
        "Bot sinyali (skor>=70, <70 çık)": score_rule(70, 70),
        "Skor>=70, <50 çık": score_rule(70, 50),
        "Trend (EMA20>EMA50, fiyat>EMA200)": trend_rule(),
    }

    curves: dict[str, pd.Series] = {}
    rows = []

    for name, rule in strategies.items():
        result = run_backtest(frames, rule, config, start=start, end=end)
        curves[name] = result.equity
        rows.append((name, result.metrics))

    window = curves[next(iter(curves))].index
    ew = buy_and_hold(frames, start=window[0], end=window[-1])
    xu = bench["close"].loc[window[0]: window[-1]]
    xu = xu / xu.iloc[0] * config.initial_capital

    curves["Eşit ağırlık al-tut"] = ew
    curves["XU100 al-tut"] = xu
    rows.append(("Eşit ağırlık al-tut", compute_metrics(ew)))
    rows.append(("XU100 al-tut", compute_metrics(xu)))

    def pct(x):
        return "-" if x is None or pd.isna(x) else f"{x * 100:+.1f}%"

    def num(x, d=2):
        return "-" if x is None or pd.isna(x) else f"{x:.{d}f}"

    lines = [
        f"Dönem: {window[0].date()} – {window[-1].date()} | {len(symbols)} hisse, "
        f"en fazla {positions} pozisyon | komisyon %{commission * 100:.2f} + kayma "
        f"%{slippage * 100:.2f} (her yön)",
    ]
    if skipped:
        lines.append(f"Veri sorunu nedeniyle dışarıda: {', '.join(skipped)}")

    lines += [
        "",
        f"{'Strateji':<36} {'Toplam':>9} {'Yıllık':>8} {'MaxDD':>8} {'Sharpe':>6} "
        f"{'İşlem':>6} {'Kazanma':>8} {'PF':>5} {'Ort.gün':>7} {'Piyasada':>8}",
    ]
    for name, m in rows:
        lines.append(
            f"{name:<36} {pct(m.get('total_return')):>9} {pct(m.get('cagr')):>8} "
            f"{pct(m.get('max_drawdown')):>8} {num(m.get('sharpe')):>6} "
            f"{m.get('trades', '-')!s:>6} {pct(m.get('win_rate')):>8} {num(m.get('profit_factor')):>5} "
            f"{num(m.get('avg_holding_days'), 0):>7} {pct(m.get('exposure')):>8}"
        )

    table = pd.DataFrame({name: yearly_returns(curve) for name, curve in curves.items()})
    lines += ["", "Yıllık getiriler:"]
    header = f"{'Yıl':<6}" + "".join(f"{n[:18]:>20}" for n in table.columns)
    lines.append(header)
    for idx, row in table.iterrows():
        lines.append(f"{idx.year:<6}" + "".join(f"{pct(v):>20}" for v in row))

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="QuantBIST backtest report")
    parser.add_argument("--positions", type=int, default=5)
    parser.add_argument("--start", default=WARMUP_START)
    parser.add_argument("--end", default=None)
    parser.add_argument("--commission", type=float, default=0.001)
    parser.add_argument("--slippage", type=float, default=0.0005)
    args = parser.parse_args(argv)

    print(
        run_report(
            positions=args.positions,
            start=args.start,
            end=args.end,
            commission=args.commission,
            slippage=args.slippage,
        )
    )


if __name__ == "__main__":
    main()
