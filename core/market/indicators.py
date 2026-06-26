"""
QuantBIST RC4
Technical Indicators
"""

from __future__ import annotations

import pandas as pd


def calculate_ma(
    close: pd.Series,
) -> tuple[float, float]:
    """
    Calculate MA20 and MA50.
    """

    ma20 = float(
        close.rolling(20).mean().iloc[-1]
    )

    ma50 = float(
        close.rolling(50).mean().iloc[-1]
    )

    return (
        round(ma20, 2),
        round(ma50, 2),
    )


def calculate_rsi(
    close: pd.Series,
) -> float:
    """
    Calculate RSI.
    """

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    gain_last = avg_gain.iloc[-1]
    loss_last = avg_loss.iloc[-1]

    if pd.isna(gain_last) or pd.isna(loss_last):
        return 50.0

    if loss_last == 0:
        return 100.0

    rs = gain_last / loss_last

    rsi = 100 - (100 / (1 + rs))

    return round(float(rsi), 2)


def calculate_macd(
    close: pd.Series,
) -> float:
    """
    Calculate MACD.
    """

    ema12 = close.ewm(
        span=12,
        adjust=False,
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False,
    ).mean()

    macd = ema12.iloc[-1] - ema26.iloc[-1]

    if pd.isna(macd):
        return 0.0

    return round(float(macd), 2)


def calculate_volatility(
    close: pd.Series,
) -> float:
    """
    Calculate volatility.
    """

    volatility = (
        close.pct_change(fill_method=None)
        .std()
    )

    if pd.isna(volatility):
        return 0.0

    return round(
        float(volatility * 100),
        2,
    )


def calculate_volume_ratio(
    volume: pd.Series,
) -> float:
    """
    Calculate volume ratio.
    """

    avg_volume = (
        volume.rolling(20)
        .mean()
        .iloc[-1]
    )

    if pd.isna(avg_volume) or avg_volume <= 0:
        return 1.0

    return round(
        float(volume.iloc[-1]) /
        float(avg_volume),
        2,
    )