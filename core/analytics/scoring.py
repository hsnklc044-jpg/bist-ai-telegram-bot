"""
QuantBIST RC5
AI Signal Scoring Engine
"""

from __future__ import annotations


# =====================================================
# SCORING ENGINE
# =====================================================


def calculate_score(
    ma20: float,
    ma50: float,
    rsi: float,
    macd: float,
    volume_ratio: float,
    volatility: float,
) -> dict[str, float | str | int]:
    """
    Calculate AI signal score.

    Score Range

    0   = Very Weak
    100 = Very Strong

    """

    bull_score = 0

    bear_score = 0


    factors: dict[str, int] = {}



    # =================================================
    # TREND ANALYSIS
    # =================================================

    if ma20 > ma50:

        bull_score += 25

        factors["trend"] = 25


    else:

        bear_score += 25

        factors["trend"] = -25



    # =================================================
    # RSI ANALYSIS
    # =================================================

    if rsi < 30:

        bull_score += 20

        factors["rsi"] = 20


    elif rsi < 40:

        bull_score += 10

        factors["rsi"] = 10


    elif rsi > 80:

        bear_score += 15

        factors["rsi"] = -15


    elif rsi > 70:

        bear_score += 10

        factors["rsi"] = -10


    else:

        factors["rsi"] = 0



    # =================================================
    # MACD ANALYSIS
    # =================================================

    if macd > 0:

        bull_score += 15

        factors["macd"] = 15


    else:

        bear_score += 15

        factors["macd"] = -15



    # =================================================
    # VOLUME ANALYSIS
    # =================================================

    if volume_ratio > 1.10:

        bull_score += 10

        factors["volume"] = 10


    elif volume_ratio < 0.80:

        bear_score += 10

        factors["volume"] = -10


    else:

        factors["volume"] = 0



    # =================================================
    # VOLATILITY ANALYSIS
    # =================================================

    # volatility = ATR / PRICE

    if volatility < 0.03:

        bull_score += 10

        factors["volatility"] = 10


    elif volatility > 0.06:

        bear_score += 10

        factors["volatility"] = -10


    else:

        factors["volatility"] = 0



    # =================================================
    # FINAL SCORE
    # =================================================

    raw_score = (

        bull_score

        -

        bear_score

    )


    score = round(

        max(

            0,

            min(

                50 + raw_score,

                100,

            ),

        ),

        0,

    )



    # =================================================
    # SIGNAL GENERATION
    # =================================================

    signal = "WATCH"

    trend = "SIDEWAYS"



    if score >= 85:

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



    # =================================================
    # CONFIDENCE
    # =================================================

    confidence = min(

        99,

        max(

            0,

            int(

                score * 0.85

                +

                volume_ratio * 8

            ),

        ),

    )



    # =================================================
    # RESULT
    # =================================================

    return {


        "bull_score":

            bull_score,


        "bear_score":

            bear_score,


        "score":

            int(score),


        "signal":

            signal,


        "trend":

            trend,


        "confidence":

            confidence,


        "factors":

            factors,

    }





__all__ = [

    "calculate_score",

]