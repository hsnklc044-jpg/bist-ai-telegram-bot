"""
QuantBIST RC4
Market Analyzer
"""

from __future__ import annotations

from core.analytics.scoring import calculate_score
from core.market.data import load_price_history
from core.market.indicators import (
    calculate_ma,
    calculate_macd,
    calculate_rsi,
    calculate_volatility,
    calculate_volume_ratio,
)


def analyze_stock(symbol: str) -> dict | None:
    """
    Analyze a stock and return signal data.
    """

    df = load_price_history(symbol)

    if df.empty:
        return None

    if len(df) < 50:
        return None

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    current_price = round(
        float(close.iloc[-1]),
        2,
    )

    ma20, ma50 = calculate_ma(close)

    rsi = calculate_rsi(close)

    macd = calculate_macd(close)

    volume_ratio = calculate_volume_ratio(volume)

    volatility = calculate_volatility(close)

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()

    tr = (
        __import__("pandas")
        .concat(
            [tr1, tr2, tr3],
            axis=1,
        )
        .max(axis=1)
    )

    atr = round(
        float(
            tr.rolling(
                14,
                min_periods=1,
            ).mean().iloc[-1]
        ),
        2,
    )

    score_data = calculate_score(
        ma20=ma20,
        ma50=ma50,
        rsi=rsi,
        macd=macd,
        volume_ratio=volume_ratio,
        volatility=volatility,
    )

    entry_price = current_price

    stop_loss = round(
        current_price - atr * 2,
        2,
    )

    target_1 = round(
        current_price + atr * 2,
        2,
    )

    target_2 = round(
        current_price + atr * 4,
        2,
    )

    return {
        "symbol": symbol,
        "price": current_price,

        **score_data,

        "rsi": rsi,
        "macd": macd,

        "volume_ratio": volume_ratio,
        "volatility": volatility,

        "atr": atr,

        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "target_1": target_1,
        "target_2": target_2,

        "ma20": ma20,
        "ma50": ma50,
    }