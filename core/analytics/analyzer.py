"""
QuantBIST RC5
Market Analyzer
"""

from __future__ import annotations


from core.analytics.scoring import calculate_score

from core.infrastructure.logger import get_logger

from core.market.data import load_price_history

from core.market.indicators import (
    generate_indicator_snapshot,
)


logger = get_logger(__name__)


# =====================================================
# HELPERS
# =====================================================


def _calculate_volume_ratio(
    df,
) -> float:
    """
    Calculate volume ratio.

    Current volume /
    Average volume
    """

    try:

        if len(df) < 20:

            return 1.0


        average_volume = (
            df["volume"]
            .rolling(20)
            .mean()
            .iloc[-1]
        )


        current_volume = (
            df["volume"]
            .iloc[-1]
        )


        if average_volume <= 0:

            return 1.0


        return round(

            current_volume /
            average_volume,

            2,

        )


    except Exception:

        return 1.0





def _generate_reason(
    snapshot,
    signal: str,
) -> list[str]:
    """
    Generate AI explanation.
    """

    reasons = []


    if snapshot.trend:

        reasons.append(

            f"Trend: {snapshot.trend.value}"

        )



    if snapshot.rsi < 30:

        reasons.append(
            "RSI oversold condition."
        )


    elif snapshot.rsi > 70:

        reasons.append(
            "RSI overbought condition."
        )


    else:

        reasons.append(
            "RSI balanced level."
        )



    if snapshot.momentum:

        reasons.append(

            f"Momentum: {snapshot.momentum}"

        )



    reasons.append(

        f"Signal: {signal}"

    )


    return reasons





def _risk_level(
    volatility: float,
) -> str:
    """
    Determine risk level.
    """

    if volatility >= 0.06:

        return "HIGH"


    if volatility >= 0.03:

        return "MEDIUM"


    return "LOW"





# =====================================================
# PUBLIC API
# =====================================================


def analyze_stock(
    symbol: str,
) -> dict | None:
    """
    Analyze stock and return RC5 signal data.
    """

    try:


        df = load_price_history(
            symbol,
        )


        if df.empty:

            return None



        snapshot = generate_indicator_snapshot(
            symbol,
        )



        volatility = round(

            snapshot.atr /
            snapshot.price,

            4,

        )



        volume_ratio = _calculate_volume_ratio(
            df,
        )



        score_data = calculate_score(

            ma20=snapshot.ema20,

            ma50=snapshot.ema50,

            rsi=snapshot.rsi,

            macd=snapshot.macd,

            volume_ratio=volume_ratio,

            volatility=volatility,

        )



        score = score_data.get(
            "score",
            0,
        )


        signal = score_data.get(
            "signal",
            "WATCH",
        )



        atr = round(
            snapshot.atr,
            2,
        )


        entry_price = round(
            snapshot.price,
            2,
        )



        return {


            "symbol":
                symbol,


            "price":
                entry_price,



            # AI SCORE

            **score_data,



            "confidence":
                score_data.get(
                    "confidence",
                    0,
                ),



            # INDICATORS

            "rsi":
                snapshot.rsi,


            "macd":
                snapshot.macd,


            "volume_ratio":
                volume_ratio,


            "volatility":
                volatility,



            "trend":
                snapshot.trend.value,


            "momentum":
                snapshot.momentum,



            # RISK

            "risk_level":
                _risk_level(
                    volatility,
                ),



            # EXPLANATION

            "reasons":
                _generate_reason(

                    snapshot,

                    signal,

                ),



            # TRADE LEVELS

            "atr":
                atr,


            "entry_price":
                entry_price,


            "stop_loss":
                round(

                    entry_price - atr * 2,

                    2,

                ),


            "target_1":
                round(

                    entry_price + atr * 2,

                    2,

                ),


            "target_2":
                round(

                    entry_price + atr * 4,

                    2,

                ),



            # MOVING AVERAGES

            "ma20":
                snapshot.ema20,


            "ma50":
                snapshot.ema50,

        }



    except Exception as exc:


        logger.exception(

            "Stock analysis failed | %s | %s",

            symbol,

            exc,

        )


        return None





__all__ = [

    "analyze_stock",

]
