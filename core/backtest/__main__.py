"""
QuantBIST
Backtest command line.

    python -m core.backtest                 # whole universe
    python -m core.backtest THYAO EREGL     # selected stocks, with trade lists
    python -m core.backtest --compare       # predefined rule sets side by side
    python -m core.backtest --no-target --trailing-atr 3 --hold-in-uptrend
"""

from __future__ import annotations

import argparse

from core.backtest.engine import BacktestConfig
from core.backtest.runner import (
    compare,
    format_comparison,
    format_portfolio,
    format_symbol,
    format_trades,
    load_dataset,
    run_portfolio,
)
from core.market.universe import load_universe


def _ticker(code: str) -> str:
    return code.strip().upper().removesuffix(".IS") + ".IS"


def main(argv: list[str] | None = None) -> None:
    defaults = BacktestConfig()

    parser = argparse.ArgumentParser(description="Backtest the QuantBIST signal.")
    parser.add_argument("symbols", nargs="*", help="hisse kodları (boşsa tüm evren)")
    parser.add_argument("--compare", action="store_true", help="zamanlama ve rotasyon kural setlerini karşılaştır")
    parser.add_argument("--commission", type=float, default=defaults.commission)
    parser.add_argument("--slippage", type=float, default=defaults.slippage)
    parser.add_argument("--stop-atr", type=float, default=defaults.stop_atr)
    parser.add_argument("--target-atr", type=float, default=defaults.target_atr)
    parser.add_argument("--no-target", action="store_true", help="sabit hedef kullanma")
    parser.add_argument("--trailing-atr", type=float, default=defaults.trailing_atr)
    parser.add_argument("--max-hold", type=int, default=defaults.max_hold_days)
    parser.add_argument(
        "--hold-in-uptrend",
        action="store_true",
        help="XU100 200 günlük ortalamanın üstündeyken sat sinyali ve süre çıkışı yok",
    )
    parser.add_argument("--entry-score", type=float, default=defaults.entry_score)
    parser.add_argument("--exit-score", type=float, default=defaults.exit_score)
    parser.add_argument("--cash-rate", type=float, default=defaults.cash_rate,
                        help="boştaki nakdin yıllık faizi, ör. 0.40")
    parser.add_argument("--keep-jumps", action="store_true",
                        help="düzeltilmemiş sıçrama içeren hisseleri de test et")
    args = parser.parse_args(argv)

    config = BacktestConfig(
        commission=args.commission,
        slippage=args.slippage,
        stop_atr=args.stop_atr,
        target_atr=None if args.no_target else args.target_atr,
        trailing_atr=args.trailing_atr,
        max_hold_days=args.max_hold,
        hold_in_uptrend=args.hold_in_uptrend,
        entry_score=args.entry_score,
        exit_score=args.exit_score,
        cash_rate=args.cash_rate,
    )

    symbols = [_ticker(s) for s in args.symbols] or load_universe()
    data = load_dataset(symbols, exclude_jumps=not args.keep_jumps)

    if not data.prices and data.skipped:
        reasons = "\n".join(f"- {s}: {why}" for s, why in data.skipped.items())
        parser.exit(1, f"Test edilecek hisse kalmadı:\n{reasons}\n")

    try:
        if args.compare:
            print(format_comparison(compare(data), data))
            return

        result = run_portfolio(data, config)
    except ValueError as exc:
        parser.exit(1, f"{exc}\nÖnce: python -m core.market.update\n")

    if len(result.results) > 1 or not args.symbols:
        print(format_portfolio(result))

    if args.symbols:
        for r in result.results:
            print()
            print(format_symbol(r))
            print()
            print(format_trades(r))


if __name__ == "__main__":
    main()
