"""
QuantBIST
Backtest command line.

    python -m core.backtest                 # whole universe
    python -m core.backtest THYAO EREGL     # selected stocks, with trade lists
    python -m core.backtest --stop-atr 1.5 --target-atr 3 --max-hold 20
"""

from __future__ import annotations

import argparse

from core.backtest.engine import BacktestConfig
from core.backtest.runner import format_portfolio, format_symbol, format_trades, run_universe
from core.market.universe import load_universe


def _ticker(code: str) -> str:
    return code.strip().upper().removesuffix(".IS") + ".IS"


def main(argv: list[str] | None = None) -> None:
    defaults = BacktestConfig()

    parser = argparse.ArgumentParser(description="Backtest the QuantBIST signal.")
    parser.add_argument("symbols", nargs="*", help="hisse kodları (boşsa tüm evren)")
    parser.add_argument("--commission", type=float, default=defaults.commission)
    parser.add_argument("--slippage", type=float, default=defaults.slippage)
    parser.add_argument("--stop-atr", type=float, default=defaults.stop_atr)
    parser.add_argument("--target-atr", type=float, default=defaults.target_atr)
    parser.add_argument("--max-hold", type=int, default=defaults.max_hold_days)
    parser.add_argument("--entry-score", type=float, default=defaults.entry_score)
    parser.add_argument("--exit-score", type=float, default=defaults.exit_score)
    args = parser.parse_args(argv)

    config = BacktestConfig(
        commission=args.commission,
        slippage=args.slippage,
        stop_atr=args.stop_atr,
        target_atr=args.target_atr,
        max_hold_days=args.max_hold,
        entry_score=args.entry_score,
        exit_score=args.exit_score,
    )

    symbols = [_ticker(s) for s in args.symbols] or load_universe()

    try:
        result = run_universe(symbols, config)
    except ValueError as exc:
        parser.exit(1, f"{exc}\nÖnce: python -m core.market.update\n")

    if len(result.results) > 1:
        print(format_portfolio(result))

    if args.symbols:
        for r in result.results:
            print()
            print(format_symbol(r))
            print()
            print(format_trades(r))


if __name__ == "__main__":
    main()
