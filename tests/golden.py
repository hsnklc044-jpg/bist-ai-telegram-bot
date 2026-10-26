"""
Golden results: the backtest output on a fixed price file.

Every later change to the engine, rules or filters must reproduce
these numbers exactly while its new options are switched off. The
prices live in a CSV (not a random seed), so the test does not depend
on numpy's random generator.

    python -m tests.golden --write-prices   # once: create the price file
    python -m tests.golden --update         # only after an intended change
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from core.backtest.engine import BacktestConfig, buy_and_hold, run_backtest
from core.strategy.filters import apply_eligibility, eligibility
from core.strategy.rules import (
    apply_rule,
    momentum_signals,
    regime_filter,
    score_rule,
    trend_rule,
    with_regime,
)

DATA_DIR = Path(__file__).parent / "data"
PRICES_FILE = DATA_DIR / "golden_prices.csv"
RESULTS_FILE = DATA_DIR / "golden_results.json"
BENCHMARK = "XU100"
SYMBOLS = [f"S{i:02d}" for i in range(1, 13)]
ROWS = 420


def write_prices() -> None:
    """Generate the fixed price file (run once; the file is committed)."""

    index = pd.bdate_range(end="2026-10-23", periods=ROWS)
    rows = []
    for k, symbol in enumerate([BENCHMARK, *SYMBOLS]):
        rng = np.random.default_rng(1000 + k)
        drift = 0.0004 + 0.0002 * (k % 5) - 0.0003 * (k % 3)
        close = 100 * np.exp(np.cumsum(rng.normal(drift, 0.02, ROWS)))
        spread = np.abs(rng.normal(0, 0.01, ROWS)) + 0.001
        frame = pd.DataFrame(
            {
                "open": close * (1 + rng.normal(0, 0.005, ROWS)),
                "high": close * (1 + spread),
                "low": close * (1 - spread),
                "close": close,
                "volume": rng.integers(1_000_000, 5_000_000, ROWS).astype(float) * (k + 1),
            },
            index=index,
        )
        if symbol == "S03":  # two locked limit-down days in a row
            for i in (300, 301):
                c = frame["close"].iloc[i - 1] * 0.9
                frame.iloc[i, :4] = [c, c, c, c]
        if symbol == "S05":  # one locked limit-up day
            c = frame["close"].iloc[249] * 1.1
            frame.iloc[250, :4] = [c, c, c, c]
        if symbol == "S07":  # gap down far below the previous close
            frame.iloc[330, 0] = frame["close"].iloc[329] * 0.8
            frame.iloc[330, 2] = frame.iloc[330, 0] * 0.99
        frame = frame.round(4)
        frame.insert(0, "symbol", symbol)
        rows.append(frame)
    out = pd.concat(rows).rename_axis("date").reset_index()
    DATA_DIR.mkdir(exist_ok=True)
    out.to_csv(PRICES_FILE, index=False, date_format="%Y-%m-%d")


def load_prices() -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    raw = pd.read_csv(PRICES_FILE, parse_dates=["date"])
    frames = {
        s: g.drop(columns="symbol").set_index("date").sort_index()
        for s, g in raw.groupby("symbol")
    }
    bench = frames.pop(BENCHMARK)
    return frames, bench


def _summary(result) -> dict:
    trades = result.trades_frame()
    return {
        "metrics": {k: (None if pd.isna(v) else v) for k, v in result.metrics.items()},
        "final_equity": float(result.equity.iloc[-1]),
        "equity_checksum": float(result.equity.sum()),
        "trades": [
            [r.symbol, str(r.entry_date), r.entry_price, str(r.exit_date), r.exit_price, r.reason]
            for r in trades.itertuples()
        ],
    }


def _special_days_rule(frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """
    Fixed entries and exits placed on the injected special days:
    S03 must sell into two locked limit-down days, S05 must buy on a
    locked limit-up day, S07 is held into a gap below its stop.
    """

    plan = {"S03": (280, 299), "S05": (249, 270), "S07": (320, 360)}
    out = {}
    for symbol, df in frames.items():
        enter = pd.Series(False, index=df.index)
        leave = pd.Series(False, index=df.index)
        if symbol in plan:
            enter.iloc[plan[symbol][0]] = True
            leave.iloc[plan[symbol][1]] = True
        out[symbol] = pd.DataFrame({"enter": enter, "exit": leave, "rank": 1.0}, index=df.index)
    return out


def scenarios() -> dict[str, dict]:
    frames, bench = load_prices()
    special = _special_days_rule(frames)
    regime = regime_filter(bench, window=100)
    start = frames["S01"].index[220]
    out = {}

    for locks in (True, False):
        out[f"special_days_locks_{'on' if locks else 'off'}"] = _summary(
            run_backtest(
                frames,
                special,
                BacktestConfig(max_positions=3, atr_stop=2.0, respect_limit_locks=locks),
                start=start,
            )
        )

    out["score_rule"] = _summary(
        run_backtest(frames, score_rule(70, 60), BacktestConfig(max_positions=4), start=start)
    )
    out["trend_rule_atr_stop"] = _summary(
        run_backtest(
            frames,
            trend_rule(10, 30, 100),
            BacktestConfig(max_positions=5, atr_stop=2.0, max_holding_days=40),
            start=start,
        )
    )
    out["trend_rule_regime_filtered"] = _summary(
        run_backtest(
            frames,
            apply_eligibility(
                with_regime(apply_rule(trend_rule(10, 30, 100), frames), regime),
                eligibility(frames, liquidity_top=8, max_run_up=0.5, run_up_window=63, max_locks=1),
                exit_when_ineligible=True,
            ),
            BacktestConfig(max_positions=5),
            start=start,
        )
    )
    out["momentum_regime"] = _summary(
        run_backtest(
            frames,
            momentum_signals(frames, lookback=63, skip=10, top_n=4, regime=regime),
            BacktestConfig(max_positions=4),
            start=start,
        )
    )
    out["no_limit_locks"] = _summary(
        run_backtest(
            frames,
            trend_rule(10, 30, 100),
            BacktestConfig(max_positions=5, respect_limit_locks=False),
            start=start,
        )
    )
    curve = buy_and_hold(frames, start=start)
    out["buy_and_hold"] = {
        "final_equity": float(curve.iloc[-1]),
        "equity_checksum": float(curve.sum()),
    }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-prices", action="store_true")
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()

    if args.write_prices:
        write_prices()
        print(f"wrote {PRICES_FILE}")
    if args.update:
        RESULTS_FILE.write_text(json.dumps(scenarios(), indent=1, sort_keys=True), encoding="utf-8")
        print(f"wrote {RESULTS_FILE}")


if __name__ == "__main__":
    main()
