"""
QuantBIST RC4
Signal Scoring Engine
"""

from __future__ import annotations


def calculate_score(
    ma20: float,
    ma50: float,
    rsi: float,
    macd: float,
    volume_ratio: float,
    volatility: float,
) -> dict[str, float | str | int]:

    bull_score = 0
    bear_score = 0

    # Trend
    if ma20 > ma50:
        bull_score += 25
    else:
        bear_score += 25

    # RSI
    if rsi < 30:
        bull_score += 20
    elif rsi < 40:
        bull_score += 10
    elif rsi > 80:
        bear_score += 15
    elif rsi > 70:
        bear_score += 10

    # MACD
    if macd > 0:
        bull_score += 15
    else:
        bear_score += 15

    # Volume
    if volume_ratio > 1.10:
        bull_score += 10
    elif volume_ratio < 0.80:
        bear_score += 10

    # Volatility
    if volatility < 2:
        bull_score += 10
    elif volatility > 6:
        bear_score += 10

    raw_score = bull_score - bear_score

    score = round(
        max(
            0,
            min(
                50 + raw_score * 0.5,
                100,
            ),
        ),
        0,
    )

    signal = "WATCH"
    trend = "SIDEWAYS"

    if score >= 80:
        signal = "STRONG BUY"
        trend = "BULLISH"

    elif score >= 70:
        signal = "BUY"
        trend = "BULLISH"

    elif score <= 20:
        signal = "STRONG SELL"
        trend = "BEARISH"

    elif score <= 35:
        signal = "SELL"
        trend = "BEARISH"

    confidence = min(
        100,
        max(
            0,
            int(score * 0.85 + volume_ratio * 8),
        ),
    )

    return {
        "bull_score": bull_score,
        "bear_score": bear_score,
        "score": score,
        "signal": signal,
        "trend": trend,
        "confidence": confidence,
    }