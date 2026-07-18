"""
QuantBIST Framework
Market Analyzer
"""

from __future__ import annotations

from core.analytics.scoring import calculate_score
from core.market.data import load_price_history
from core.market.indicators import generate_indicator_snapshot


def analyze_stock(symbol: str) -> dict | None:
    """
    Analyze a stock and return signal data.
    """

    df = load_price_history(symbol)

    if df.empty:
        return None

    snapshot = generate_indicator_snapshot(symbol)

    score_data = calculate_score(

        ma20=snapshot.ema20,

        ma50=snapshot.ema50,

        rsi=snapshot.rsi,

        macd=snapshot.macd,

        volume_ratio=1.0,

        volatility=round(
            snapshot.atr / snapshot.price,
            4,
        ),

    )

    atr = round(snapshot.atr, 2)

    entry_price = round(snapshot.price, 2)

    stop_loss = round(

        entry_price - atr * 2,

        2,

    )

    target_1 = round(

        entry_price + atr * 2,

        2,

    )

    target_2 = round(

        entry_price + atr * 4,

        2,

    )

    return {

        "symbol": symbol,

        "price": entry_price,

        **score_data,

        "rsi": snapshot.rsi,

        "macd": snapshot.macd,

        "volume_ratio": 1.0,

        "volatility": round(
            snapshot.atr / snapshot.price,
            4,
        ),

        "atr": atr,

        "entry_price": entry_price,

        "stop_loss": stop_loss,

        "target_1": target_1,

        "target_2": target_2,

        "ma20": snapshot.ema20,

        "ma50": snapshot.ema50,

        "trend": snapshot.trend.value,

        "momentum": snapshot.momentum,

    }